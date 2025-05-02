/**
 * 오디오 녹음 관리 JavaScript 파일
 * 브라우저의 MediaRecorder API를 사용하여 오디오 녹음 기능을 구현합니다.
 */

// 레코더 객체
let recorder = {
    stream: null,
    mediaRecorder: null,
    audioChunks: [],
    
    /**
     * 녹음 초기화 및 시작
     */
    start: function() {
        this.audioChunks = [];
        
        // 마이크 접근 권한 요청
        navigator.mediaDevices.getUserMedia({ audio: true, video: false })
            .then(stream => {
                this.stream = stream;
                
                // MediaRecorder 초기화
                this.mediaRecorder = new MediaRecorder(stream);
                
                // 데이터 수집 이벤트 핸들러
                this.mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        this.audioChunks.push(event.data);
                    }
                };
                
                // 녹음 시작
                this.mediaRecorder.start();
                console.log('녹음이 시작되었습니다.');
            })
            .catch(error => {
                console.error('마이크 접근 오류:', error);
                alert('마이크에 접근할 수 없습니다. 브라우저 권한을 확인해주세요.');
                
                // 상태 업데이트
                document.getElementById('recording-status-text').textContent = '마이크 접근 오류';
                document.getElementById('start-recording').disabled = false;
                document.getElementById('recording-indicator').classList.remove('recording');
            });
    },
    
    /**
     * 녹음 종료 및 처리
     * @param {Function} callback - 녹음 완료 후 실행할 콜백 함수
     */
    stop: function(callback) {
        // MediaRecorder가 초기화되지 않은 경우
        if (!this.mediaRecorder) {
            console.error('MediaRecorder가 초기화되지 않았습니다.');
            return;
        }
        
        // 녹음 종료 이벤트 핸들러
        this.mediaRecorder.onstop = () => {
            // 오디오 데이터 처리
            const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
            
            // 콜백 함수 호출
            if (callback && typeof callback === 'function') {
                callback(audioBlob);
            }
            
            // 스트림 트랙 종료
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
            }
            
            console.log('녹음이 종료되었습니다.');
        };
        
        // 녹음 중인 경우에만 종료
        if (this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
        }
    },
    
    /**
     * 현재 녹음 상태 확인
     * @returns {boolean} 녹음 중인지 여부
     */
    isRecording: function() {
        return this.mediaRecorder !== null && this.mediaRecorder.state === 'recording';
    }
};

// 브라우저 호환성 체크
document.addEventListener('DOMContentLoaded', () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.error('브라우저가 getUserMedia API를 지원하지 않습니다.');
        alert('이 브라우저는 녹음 기능을 지원하지 않습니다. 최신 버전의 Chrome, Firefox, Safari 등을 사용해주세요.');
        
        // 녹음 버튼 비활성화
        document.getElementById('start-recording').disabled = true;
        document.getElementById('recording-status-text').textContent = '브라우저 호환성 오류';
    }
});
