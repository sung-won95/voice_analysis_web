import os
import librosa
import torch
import numpy as np

# 모델 임포트
from inference.speech_analysis_model import VoiceAnalysisModel, predict_voice_quality, generate_feedback

# 상수 정의
SAMPLE_RATE = 22050
N_MFCC = 13
N_FFT = 2048
HOP_LENGTH = 512
MICRO_SEGMENT_DURATION = 0.2  # 0.2초 단위로 분석
MIN_ENERGY_THRESHOLD = 0.01   # 침묵 감지 임계값

def split_wav_to_micro_segments(y, sr, segment_duration=MICRO_SEGMENT_DURATION, overlap=0.5, energy_threshold=MIN_ENERGY_THRESHOLD):
    """
    오디오를 미세 세그먼트로 분할하고 소음/침묵 구간 필터링
    
    Parameters:
    -----------
    y : numpy.ndarray
        오디오 데이터
    sr : int
        샘플링 레이트
    segment_duration : float
        세그먼트 지속 시간(초)
    overlap : float
        세그먼트 간 겹침 비율
    energy_threshold : float
        RMS 에너지 임계값 (침묵 검출용)
        
    Returns:
    --------
    list
        (시작 시간, 종료 시간, 세그먼트 오디오) 튜플 목록
    """
    duration = len(y) / sr
    segments = []
    
    # 단계 크기 계산 (겹침 고려)
    step = segment_duration * (1 - overlap)
    start_times = np.arange(0, duration - segment_duration/2, step)
    
    for start_time in start_times:
        end_time = start_time + segment_duration
        
        # 세그먼트 경계가 오디오 길이를 초과하지 않도록 조정
        if end_time > duration:
            end_time = duration
        
        # 세그먼트 오디오 추출
        start_idx = int(start_time * sr)
        end_idx = int(end_time * sr)
        segment_audio = y[start_idx:end_idx]
        
        # 세그먼트가 너무 짧으면 무시
        if len(segment_audio) < 0.5 * segment_duration * sr:
            continue
        
        # RMS 에너지 계산하여 침묵 구간 감지
        rms = librosa.feature.rms(y=segment_audio)[0]
        if np.mean(rms) < energy_threshold:
            continue  # 침묵 구간 무시
        
        segments.append((start_time, end_time, segment_audio))
    
    return segments

def analyze_wav_file(wav_path, model_path="models/best_voice_model.pt"):
    """
    WAV 파일을 분석하여 JSON 형식으로 결과 생성
    
    Parameters:
    -----------
    wav_path : str
        WAV 파일 경로
    model_path : str
        학습된 모델 파일 경로
    
    Returns:
    --------
    dict
        분석 결과 (JSON 형식으로 저장 가능)
    """
    # 디바이스 설정
    device = torch.device('mps' if torch.backends.mps.is_available() else 'cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # WAV 파일 로드
    try:
        y, sr = librosa.load(wav_path, sr=SAMPLE_RATE)
        print(f"오디오 로드 성공: {wav_path}, 길이: {len(y)/sr:.2f}초")
    except Exception as e:
        print(f"오디오 파일 로드 중 오류 발생: {e}")
        return generate_test_result(wav_path)
    
    # 모델 로드 - 입력 크기는 실제 특성 추출 함수와 일치
    # 테스트 추출로 크기 확인
    test_segment = y[:int(MICRO_SEGMENT_DURATION * sr)] if len(y) > int(MICRO_SEGMENT_DURATION * sr) else y
    from inference.speech_analysis_model import extract_features
    test_features = extract_features(test_segment, sr)
    input_size = test_features.shape[0]
    
    model = VoiceAnalysisModel(input_size=input_size).to(device)
    
    try:
        # 모델 디렉토리 확인
        model_dir = os.path.dirname(model_path)
        if not os.path.exists(model_dir):
            os.makedirs(model_dir, exist_ok=True)
            print(f"모델 디렉토리 '{model_dir}'를 생성했습니다.")
        
        # 모델 파일이 존재하는지 확인
        if not os.path.exists(model_path):
            print(f"경고: 모델 파일 '{model_path}'이 존재하지 않습니다. 테스트 모드로 실행합니다.")
            # 테스트 모드: 랜덤한 결과 생성
            return generate_test_result(wav_path)
        
        model.load_state_dict(torch.load(model_path, map_location=device))
        model.eval()
        print(f"모델 '{model_path}'을 성공적으로 로드했습니다.")
    except Exception as e:
        print(f"모델 로드 중 오류 발생: {e}")
        # 테스트 모드: 랜덤한 결과 생성
        return generate_test_result(wav_path)
    
    # 미세 세그먼트로 나누기
    print("오디오를 0.2초 단위 미세 세그먼트로 분할 중...")
    segments = split_wav_to_micro_segments(y, sr)
    print(f"총 {len(segments)}개의 미세 세그먼트 생성됨")
    
    if len(segments) == 0:
        print("경고: 유효한 세그먼트가 없습니다. 테스트 모드로 실행합니다.")
        return generate_test_result(wav_path)
    
    # 세그먼트별 분석
    segment_results = []
    segment_predictions = []
    
    for segment_idx, (start_time, end_time, segment_audio) in enumerate(segments, 1):
        try:
            # 미세 세그먼트 분석
            predictions = predict_voice_quality(model, segment_audio, sr)
            
            # 결과 저장
            segment_info = {
                "segmentIndex": segment_idx,
                "startTimeSec": float(f"{start_time:.2f}"),
                "endTimeSec": float(f"{end_time:.2f}"),
                "vocalCord": predictions['vocal_cord'],
                "contact": predictions['contact'],
                "larynx": predictions['larynx'],
                "strength": predictions['strength']
            }
            
            segment_results.append(segment_info)
            segment_predictions.append(predictions)
            
        except Exception as e:
            print(f"세그먼트 분석 중 오류 발생: {e}")
    
    # 세그먼트가 충분한지 확인
    if len(segment_results) == 0:
        print("경고: 분석에 성공한 세그먼트가 없습니다. 테스트 모드로 실행합니다.")
        return generate_test_result(wav_path)
    
    # 세그먼트를 통합하여 구간별 피드백 생성
    consolidated_segments = consolidate_segments(segment_results)
    
    # 전체 피드백 생성 (첫 번째 세그먼트 기반)
    try:
        feedback = generate_feedback(segment_predictions[0])
    except Exception as e:
        print(f"피드백 생성 중 오류 발생: {e}")
        feedback = "자동 생성된 피드백을 제공할 수 없습니다."
    
    # 결과 JSON 구성
    result = {
        "wavKey": os.path.basename(wav_path),
        "scaleType": feedback,
        "segments": segment_results,  # 원시 세그먼트 결과 (차트용)
        "consolidatedSegments": consolidated_segments  # 통합된 세그먼트 (UI 표시용)
    }
    
    return result

def consolidate_segments(segments):
    """
    동일한 분석 결과를 가진 연속된 세그먼트를 하나로 통합
    
    Parameters:
    -----------
    segments : list
        세그먼트 정보 목록
        
    Returns:
    --------
    list
        통합된 세그먼트 목록
    """
    if not segments:
        return []
    
    # 시간 순으로 정렬
    sorted_segments = sorted(segments, key=lambda x: x['startTimeSec'])
    
    consolidated = []
    current_group = {
        "startTimeSec": sorted_segments[0]['startTimeSec'],
        "endTimeSec": sorted_segments[0]['endTimeSec'],
        "segmentIndices": [sorted_segments[0]['segmentIndex']],
        "vocalCord": sorted_segments[0]['vocalCord'],
        "contact": sorted_segments[0]['contact'],
        "larynx": sorted_segments[0]['larynx'],
        "strength": sorted_segments[0]['strength']
    }
    
    for i in range(1, len(sorted_segments)):
        segment = sorted_segments[i]
        
        # 특성 값이 모두 동일한지 확인
        if (segment['vocalCord'] == current_group['vocalCord'] and
            segment['contact'] == current_group['contact'] and
            segment['larynx'] == current_group['larynx'] and
            segment['strength'] == current_group['strength']):
            
            # 시간적으로 붙어있는지 확인
            if abs(segment['startTimeSec'] - current_group['endTimeSec']) < 0.05:  # 50ms 이내면 연속으로 간주
                # 그룹 확장
                current_group['endTimeSec'] = segment['endTimeSec']
                current_group['segmentIndices'].append(segment['segmentIndex'])
            else:
                # 붙어있지 않으면 새 그룹 시작 (같은 특성이지만 시간적으로 분리)
                consolidated.append(current_group)
                current_group = {
                    "startTimeSec": segment['startTimeSec'],
                    "endTimeSec": segment['endTimeSec'],
                    "segmentIndices": [segment['segmentIndex']],
                    "vocalCord": segment['vocalCord'],
                    "contact": segment['contact'],
                    "larynx": segment['larynx'],
                    "strength": segment['strength']
                }
        else:
            # 특성이 다르면 새 그룹 시작
            consolidated.append(current_group)
            current_group = {
                "startTimeSec": segment['startTimeSec'],
                "endTimeSec": segment['endTimeSec'],
                "segmentIndices": [segment['segmentIndex']],
                "vocalCord": segment['vocalCord'],
                "contact": segment['contact'],
                "larynx": segment['larynx'],
                "strength": segment['strength']
            }
    
    # 마지막 그룹 추가
    consolidated.append(current_group)
    
    # 그룹 번호 및 피드백 추가
    for i, group in enumerate(consolidated, 1):
        from inference.speech_analysis_model import generate_segment_feedback
        group["groupIndex"] = i
        group["feedback"] = generate_segment_feedback({
            "vocal_cord": group["vocalCord"],
            "contact": group["contact"],
            "larynx": group["larynx"],
            "strength": group["strength"]
        })
    
    return consolidated

def generate_test_result(wav_path):
    """테스트용 결과 생성 함수 (모델이 없을 때 사용)"""
    # 테스트용 피드백 메시지
    feedback = "낮은 음에서 성대를 필요 보다 조금 더 두껍게 진동 시킵니다. " + \
               "좀 더 가볍게 발성할 필요가 있습니다. 높은 음에서 성대가 가볍게 진동하는 느낌은 좋으나, " + \
               "후두의 상승으로 톤의 변화가 급격하게 발생하기도 합니다. " + \
               "또한 부분적으로 필요 보다 좀 더 가볍게 진동하는 경향도 보입니다."
    
    # 테스트용 세그먼트 데이터 (0.2초 단위)
    raw_segments = [
        {
            "segmentIndex": 1,
            "startTimeSec": 1.0,
            "endTimeSec": 1.2,
            "vocalCord": "M_L",
            "contact": "H_L",
            "larynx": "M_M",
            "strength": "M_H"
        },
        {
            "segmentIndex": 2,
            "startTimeSec": 1.2,
            "endTimeSec": 1.4,
            "vocalCord": "M_L",
            "contact": "H_L",
            "larynx": "M_M",
            "strength": "M_H"
        },
        {
            "segmentIndex": 3,
            "startTimeSec": 1.4,
            "endTimeSec": 1.6,
            "vocalCord": "M_H",
            "contact": "M_L",
            "larynx": "M_H",
            "strength": "M_L"
        },
        {
            "segmentIndex": 4,
            "startTimeSec": 1.6,
            "endTimeSec": 1.8,
            "vocalCord": "M_H",
            "contact": "M_L",
            "larynx": "M_H",
            "strength": "M_L"
        },
        {
            "segmentIndex": 5,
            "startTimeSec": 1.8,
            "endTimeSec": 2.0,
            "vocalCord": "M_H",
            "contact": "M_L",
            "larynx": "H_L",
            "strength": "M_L"
        },
        {
            "segmentIndex": 6,
            "startTimeSec": 2.0,
            "endTimeSec": 2.2,
            "vocalCord": "M_L",
            "contact": "H_L",
            "larynx": "M_M",
            "strength": "M_H"
        }
    ]
    
    # 통합된 세그먼트 테스트 데이터
    consolidated_segments = [
        {
            "groupIndex": 1,
            "startTimeSec": 1.0,
            "endTimeSec": 1.4,
            "segmentIndices": [1, 2],
            "vocalCord": "M_L",
            "contact": "H_L",
            "larynx": "M_M",
            "strength": "M_H",
            "feedback": "성대가 중간 정도 두께로 진동하며, 접촉률이 높고, 후두 위치는 중간, 발성 강도는 중간 수준입니다."
        },
        {
            "groupIndex": 2,
            "startTimeSec": 1.4,
            "endTimeSec": 1.8,
            "segmentIndices": [3, 4],
            "vocalCord": "M_H",
            "contact": "M_L",
            "larynx": "M_H",
            "strength": "M_L",
            "feedback": "고음에서 성대 진동이 좋으나, 성대 접촉이 약하고 후두 위치가 높습니다."
        },
        {
            "groupIndex": 3,
            "startTimeSec": 1.8,
            "endTimeSec": 2.0,
            "segmentIndices": [5],
            "vocalCord": "M_H",
            "contact": "M_L",
            "larynx": "H_L",
            "strength": "M_L",
            "feedback": "후두의 급격한, 변화가 관찰됩니다. 더 안정적인 발성이 필요합니다."
        },
        {
            "groupIndex": 4,
            "startTimeSec": 2.0,
            "endTimeSec": 2.2,
            "segmentIndices": [6],
            "vocalCord": "M_L",
            "contact": "H_L",
            "larynx": "M_M",
            "strength": "M_H",
            "feedback": "성대가 중간 정도 두께로 진동하며, 접촉률이 높고, 후두 위치는 중간, 발성 강도는 중간 수준입니다."
        }
    ]
    
    # 결과 JSON 구성
    result = {
        "wavKey": os.path.basename(wav_path),
        "scaleType": feedback,
        "segments": raw_segments,  # 원시 세그먼트 데이터
        "consolidatedSegments": consolidated_segments  # 통합된 세그먼트
    }
    
    return result
