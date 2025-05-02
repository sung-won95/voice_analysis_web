import os
import json
import uuid
import torch
from flask import Flask, render_template, request, jsonify
import soundfile as sf
import numpy as np

# 인퍼런스 모듈 불러오기
from inference.speech_analysis import analyze_wav_file

app = Flask(__name__)

# 상수 정의
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'wav'}
MODEL_PATH = 'models/best_voice_model.pt'

# 앱 설정
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 제한

# 폴더가 없으면 생성
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/scales')
def get_scales():
    """사용 가능한 스케일 목록 반환"""
    scales_dir = os.path.join('static', 'scales')
    scales = []
    
    if os.path.exists(scales_dir):
        for file in os.listdir(scales_dir):
            if file.endswith('.wav') or file.endswith('.mp3'):
                scale_name = os.path.splitext(file)[0]
                scale_path = os.path.join('scales', file)
                scales.append({
                    'name': scale_name,
                    'path': scale_path
                })
    
    # 스케일 파일이 없는 경우
    if not scales:
        # 기본 스케일 추가
        scales = [
            {'name': 'C 5도 스케일', 'path': 'scales/c_scale.wav'},
            {'name': 'D 5도 스케일', 'path': 'scales/d_scale.wav'},
            {'name': 'E 5도 스케일', 'path': 'scales/e_scale.wav'},
            {'name': 'F 5도 스케일', 'path': 'scales/f_scale.wav'},
            {'name': 'G 5도 스케일', 'path': 'scales/g_scale.wav'},
            {'name': 'A 5도 스케일', 'path': 'scales/a_scale.wav'},
            {'name': 'B 5도 스케일', 'path': 'scales/b_scale.wav'}
        ]
    
    return jsonify(scales)

@app.route('/upload', methods=['POST'])
def upload_audio():
    """녹음된 오디오 업로드, 저장 및 분석"""
    if 'audio' not in request.files:
        return jsonify({'error': '오디오 파일이 없습니다.'}), 400
    
    file = request.files['audio']
    
    if file.filename == '':
        return jsonify({'error': '선택된 파일이 없습니다.'}), 400
    
    if not file or not allowed_file(file.filename):
        return jsonify({'error': '허용되지 않는 파일 형식입니다.'}), 400
    
    # 고유한 파일명 생성
    filename = f"{uuid.uuid4()}.wav"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # 파일 저장
    file.save(filepath)
    
    # 분석 진행 (새로운 미세 세그먼트 분석 적용)
    try:
        print(f"파일 '{filepath}'에 대한 분석 시작...")
        result = analyze_wav_file(filepath, MODEL_PATH)
        
        if result is None:
            return jsonify({'error': '분석에 실패했습니다.'}), 500
        
        # 결과 반환
        return jsonify({'success': True, 'filename': filename, 'result': result})
    
    except Exception as e:
        return jsonify({'error': f'분석 중 오류 발생: {str(e)}'}), 500

if __name__ == '__main__':
    # 디바이스 설정 (로그용)
    device = torch.device('mps' if torch.backends.mps.is_available() else 'cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    app.run(debug=True)
