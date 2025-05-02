import torch
import torch.nn as nn
import torch.nn.functional as F
import librosa
import numpy as np

# 상수 정의
SAMPLE_RATE = 22050
N_MFCC = 13
N_FFT = 2048
HOP_LENGTH = 512
MICRO_SEGMENT_DURATION = 0.2  # 0.2초 단위 세그먼트

class VoiceAnalysisModel(nn.Module):
    """음성 분석을 위한 딥러닝 모델"""
    
    def __init__(self, input_size=63, hidden_size1=256, hidden_size2=128, hidden_size3=64):
        super(VoiceAnalysisModel, self).__init__()
        
        # 특성 추출 레이어 - 학습된 모델과 일치하도록 설정
        self.shared_layers = nn.Sequential(
            nn.Linear(input_size, hidden_size1),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_size1, hidden_size2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_size2, hidden_size3),
            nn.ReLU()
        )
        
        # 분류 헤드 (모든 헤드는 6개 클래스로)
        self.vocal_cord_head = nn.Linear(hidden_size3, 6)
        self.contact_head = nn.Linear(hidden_size3, 6)
        self.larynx_head = nn.Linear(hidden_size3, 6)
        self.strength_head = nn.Linear(hidden_size3, 6)
    
    def forward(self, x):
        # 특성 추출
        x = self.shared_layers(x)
        
        # 각 특성에 대한 분류
        vocal_cord = self.vocal_cord_head(x)
        contact = self.contact_head(x)
        larynx = self.larynx_head(x)
        strength = self.strength_head(x)
        
        return {
            'vocal_cord': vocal_cord,
            'contact': contact,
            'larynx': larynx,
            'strength': strength
        }

def extract_features(audio, sr=SAMPLE_RATE):
    """
    오디오에서 특성 추출 - 미세 세그먼트 특화 기능 추가
    
    Parameters:
    -----------
    audio : numpy.ndarray
        오디오 데이터
    sr : int
        샘플링 레이트
            
    Returns:
    --------
    numpy.ndarray
        추출된 특성 벡터
    """
    # 오디오가 너무 짧은 경우 패딩
    min_samples = int(0.1 * sr)  # 최소 0.1초
    if len(audio) < min_samples:
        audio = np.pad(audio, (0, min_samples - len(audio)), 'constant')
    
    # MFCC 추출
    mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=N_MFCC, n_fft=N_FFT, hop_length=HOP_LENGTH)
    mfccs = np.mean(mfccs.T, axis=0)  # 평균값으로 요약
    
    # 스펙트로그램 추출
    mel_spec = librosa.feature.melspectrogram(y=audio, sr=sr, n_fft=N_FFT, hop_length=HOP_LENGTH)
    log_mel_spec = librosa.power_to_db(mel_spec)
    log_mel_spec = np.mean(log_mel_spec, axis=1)  # 주파수 차원으로 평균
    
    # 제로 크로싱 레이트, 스펙트럴 센트로이드, 피치 추정
    zero_crossing = librosa.feature.zero_crossing_rate(audio)
    zero_crossing = np.mean(zero_crossing)
    spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)
    spectral_centroid = np.mean(spectral_centroid)
    pitches, magnitudes = librosa.piptrack(y=audio, sr=sr, n_fft=N_FFT, hop_length=HOP_LENGTH)
    pitch_mean = np.mean(pitches[magnitudes > 0]) if np.any(magnitudes > 0) else 0
    
    # 추가 특성
    # RMS 에너지 (볼륨)
    rms = librosa.feature.rms(y=audio)[0]
    rms_mean = np.mean(rms)
    rms_var = np.var(rms)
    
    # 스펙트럴 플럭스 (스펙트럼 변화율)
    spec_flux = np.mean(librosa.onset.onset_strength(y=audio, sr=sr))
    
    # 스펙트럴 롤오프 (주파수 에너지 분포)
    rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr)[0]
    rolloff_mean = np.mean(rolloff)
    
    # 스펙트럴 대비 (고주파 대역 대비)
    contrast = librosa.feature.spectral_contrast(y=audio, sr=sr)
    contrast_mean = np.mean(contrast)
    
    # 시간적 특성 (미세 세그먼트 시작/중간/끝 RMS)
    n_frames = len(rms)
    if n_frames >= 3:
        rms_start = np.mean(rms[:n_frames//3])
        rms_middle = np.mean(rms[n_frames//3:(2*n_frames)//3])
        rms_end = np.mean(rms[(2*n_frames)//3:])
    else:
        rms_start = rms_middle = rms_end = rms_mean
    
    # 특성 결합
    features = np.concatenate([
        mfccs, 
        log_mel_spec, 
        [zero_crossing, spectral_centroid, pitch_mean, 
         rms_mean, rms_var, spec_flux, rolloff_mean, contrast_mean,
         rms_start, rms_middle, rms_end]
    ])
    
    print(f"특성 벡터 차원: {features.shape}")
    
    return features

def decode_label(outputs):
    """
    모델 출력을 라벨 문자열로 디코딩
    
    Parameters:
    -----------
    outputs : torch.Tensor
        모델 출력 텐서 (6개 요소: 앞 3개는 시작 상태, 뒤 3개는 종료 상태)
        
    Returns:
    --------
    str
        디코딩된 라벨 (예: 'H_L')
    """
    mapping = {0: 'L', 1: 'M', 2: 'H'}
    
    # 첫번째 부분 (앞의 3개 요소)
    first_probs = outputs[:3]
    first_idx = torch.argmax(first_probs).item()
    
    # 두번째 부분 (뒤의 3개 요소)
    second_probs = outputs[3:]
    second_idx = torch.argmax(second_probs).item()
    
    return f"{mapping[first_idx]}_{mapping[second_idx]}"

def predict_voice_quality(model, audio, sr=SAMPLE_RATE):
    """음성 품질 예측 함수"""
    # 디바이스 설정
    device = next(model.parameters()).device
    
    # 특성 추출
    features = extract_features(audio, sr)
    
    # 텐서로 변환 및 배치 차원 추가
    features_tensor = torch.FloatTensor(features).unsqueeze(0).to(device)
    
    # 예측
    with torch.no_grad():
        outputs = model(features_tensor)
        
        # 각 특성에 대한 출력 디코딩
        predictions = {}
        for key, value in outputs.items():
            pred_tensor = value[0]  # 첫 번째(유일한) 배치 항목
            
            # 라벨 디코딩
            predictions[key] = decode_label(pred_tensor)
    
    return predictions

def generate_segment_feedback(predictions):
    """
    개별 세그먼트에 대한 간결한 피드백 생성
    
    Parameters:
    -----------
    predictions : dict
        예측 결과 (특성별 라벨)
        
    Returns:
    --------
    str
        세그먼트별 피드백
    """
    # 성대 진동 분석
    vc_first, vc_second = predictions['vocal_cord'].split('_')
    
    # 접촉률 분석
    cont_first, cont_second = predictions['contact'].split('_')
    
    # 후두 위치 분석
    larynx_first, larynx_second = predictions['larynx'].split('_')
    
    # 발성 강도 분석
    str_first, str_second = predictions['strength'].split('_')
    
    # 주요 특성 조합에 따른 맞춤형 피드백
    if vc_first == 'M' and vc_second == 'L' and cont_first == 'H':
        return "성대가 중간 정도 두께로 진동하며, 접촉률이 높고, 후두 위치는 중간, 발성 강도는 중간 수준입니다."
    
    elif vc_first == 'M' and vc_second == 'H' and larynx_first == 'M' and larynx_second == 'H':
        return "고음에서 성대 진동이 좋으나, 성대 접촉이 약하고 후두 위치가 높습니다."
    
    elif larynx_first == 'H' and larynx_second == 'L':
        return "후두의 급격한 변화가 관찰됩니다. 더 안정적인 발성이 필요합니다."
    
    elif vc_first == 'H':
        return "성대가 두껍게 진동하고 있습니다. 더 가볍게 발성해 보세요."
    
    elif cont_first == 'L':
        return "성대 접촉이 약합니다. 더 명확한 발성이 필요합니다."
    
    elif str_first == 'H':
        return "발성 강도가 강합니다. 좀 더 부드럽게 발성해 보세요."
    
    # 기본 피드백 (특별한 패턴 없는 경우)
    return f"성대 진동: {predictions['vocal_cord']}, 접촉: {predictions['contact']}, " + \
           f"후두 위치: {predictions['larynx']}, 발성 강도: {predictions['strength']}"

def generate_feedback(predictions):
    """
    전체 피드백 생성 함수 (종합 분석)
    
    Parameters:
    -----------
    predictions : dict
        예측 결과 (특성별 라벨)
        
    Returns:
    --------
    str
        생성된 피드백 문자열
    """
    feedback = ""
    
    # 1. 성대 진동 분석
    vc_first, vc_second = predictions['vocal_cord'].split('_')
    if vc_first == 'L':
        feedback += "낮은 음에서 성대를 필요보다 두껍게 진동시킵니다. 좀 더 가볍게 발성할 필요가 있습니다. "
    elif vc_first == 'H':
        feedback += "낮은 음에서 성대를 필요보다 가볍게 진동시킵니다. 좀 더 안정적인 발성이 필요합니다. "
    
    if vc_second != vc_first:
        if vc_second == 'H':
            feedback += "높은 음에서 성대가 가볍게 진동하는 느낌은 좋으나, "
        elif vc_second == 'L':
            feedback += "높은 음에서 성대가 무겁게 진동하는 경향이 있습니다. "
    
    # 2. 접촉률 분석
    cont_first, cont_second = predictions['contact'].split('_')
    if cont_first == 'L':
        feedback += "성대 접촉률이 낮아 소리가 흐릴 수 있습니다. "
    elif cont_first == 'H':
        feedback += "성대 접촉률이 높아 소리가 긴장될 수 있습니다. "
    
    # 3. 후두 위치 분석
    larynx_first, larynx_second = predictions['larynx'].split('_')
    if larynx_first == 'H' and larynx_second == 'L':
        feedback += "후두의 상승으로 톤의 변화가 급격하게 발생하기도 합니다. "
    elif larynx_first == 'H':
        feedback += "후두 위치가 전반적으로 높은 편입니다. "
    elif larynx_first == 'L':
        feedback += "후두 위치가 전반적으로 낮은 편입니다. "
    
    # 4. 발성 강도 분석
    str_first, str_second = predictions['strength'].split('_')
    if str_first == 'L':
        feedback += "발성 강도가 전반적으로 약한 편입니다. "
    elif str_first == 'H':
        feedback += "발성 강도가 전반적으로 강한 편입니다. "
    
    # 5. 추가 분석
    if 'H' in predictions['vocal_cord'] and 'H' in predictions['larynx']:
        feedback += "또한 부분적으로 필요보다 좀 더 가볍게 진동하는 경향도 보입니다. "
    
    return feedback.strip()
