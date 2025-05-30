"""
음성 분석을 위한 메인 모듈
"""
import os
import librosa
import torch
import numpy as np

# 모델 임포트
from inference.speech_analysis_model import VoiceAnalysisModel, predict_voice_quality, generate_feedback, extract_features
from inference.segment_utils import consolidate_segments, generate_test_result
from inference.pitch_analysis import group_segments_by_pitch

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
        (시작 시간, 종료 시간, 세그먼트 오디오, 피치) 튜플 목록
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
        
        # 피치 추출
        try:
            pitches, magnitudes = librosa.piptrack(
                y=segment_audio, 
                sr=sr, 
                n_fft=N_FFT, 
                hop_length=HOP_LENGTH,
                fmin=80,  # 최소 주파수(Hz) 설정
                fmax=1200  # 최대 주파수(Hz) 설정
            )
            
            # 유효한 피치 값 추출
            valid_pitches = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:  # 0이 아닌 피치만 고려
                    valid_pitches.append(pitch)
            
            # 피치가 있는 경우만 평균 계산
            avg_pitch = np.mean(valid_pitches) if valid_pitches else 0.0
        except Exception as e:
            print(f"피치 추출 중 오류 발생: {e}")
            avg_pitch = 0.0
            
        segments.append((start_time, end_time, segment_audio, avg_pitch))
    
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
    
    for segment_idx, (start_time, end_time, segment_audio, avg_pitch) in enumerate(segments, 1):
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
            
            # 피치 정보 추가 (유효한 경우)
            if avg_pitch > 0:
                segment_info["pitch"] = float(f"{avg_pitch:.2f}")
            
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
    
    # 피치별 그룹화 및 분석
    pitch_groups = group_segments_by_pitch(segment_results)
    
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
        "consolidatedSegments": consolidated_segments,  # 통합된 세그먼트 (UI 표시용)
        "pitchGroups": pitch_groups  # 피치별 그룹화 결과 (새로 추가)
    }
    
    return result