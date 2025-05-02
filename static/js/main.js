/**
 * 메인 JavaScript 파일
 * 애플리케이션의 흐름과 전반적인 기능을 관리합니다.
 */

// 전역 변수 선언
let selectedScale = null;
let recordedBlob = null;
let analysisResult = null;
let visualizationChart = null;

// DOM 요소들
const playScaleButton = document.getElementById('play-scale');
const startRecordingButton = document.getElementById('start-recording');
const stopRecordingButton = document.getElementById('stop-recording');
const analyzeButton = document.getElementById('analyze-button');
const recordingStatusText = document.getElementById('recording-status-text');
const recordingIndicator = document.getElementById('recording-indicator');
const analysisStatusText = document.getElementById('analysis-status-text');
const analysisLoader = document.getElementById('analysis-loader');
const recordedAudio = document.getElementById('recorded-audio');
const scalePlayer = document.getElementById('scale-player');
const selectedScaleText = document.getElementById('selected-scale');
const analysisResultsSection = document.getElementById('analysis-results');
const wavKeyElement = document.getElementById('wav-key');
const scaleTypeElement = document.getElementById('scale-type');
const segmentsListElement = document.getElementById('segments-list');
const visualizationChartElement = document.getElementById('visualization-chart');

// 이벤트 리스너 등록
document.addEventListener('DOMContentLoaded', () => {
    // 스케일 목록 로드
    loadScales();
    
    // 버튼 이벤트 리스너
    playScaleButton.addEventListener('click', playSelectedScale);
    startRecordingButton.addEventListener('click', startRecording);
    stopRecordingButton.addEventListener('click', stopRecording);
    analyzeButton.addEventListener('click', analyzeRecording);
});

/**
 * 선택된 스케일 재생
 */
function playSelectedScale() {
    if (selectedScale) {
        scalePlayer.play();
    }
}

/**
 * 녹음 시작
 */
function startRecording() {
    // 녹음 상태 업데이트
    recordingStatusText.textContent = '녹음 중...';
    recordingIndicator.classList.add('recording');
    
    // 버튼 상태 업데이트
    startRecordingButton.disabled = true;
    stopRecordingButton.disabled = false;
    
    // 녹음 시작
    recorder.start();
}

/**
 * 녹음 종료
 */
function stopRecording() {
    // 녹음 상태 업데이트
    recordingStatusText.textContent = '녹음 완료';
    recordingIndicator.classList.remove('recording');
    
    // 버튼 상태 업데이트
    stopRecordingButton.disabled = true;
    
    // 녹음 종료
    recorder.stop(processRecording);
}

/**
 * 녹음 파일 처리
 * @param {Blob} blob - 녹음된 오디오 블롭
 */
function processRecording(blob) {
    // 녹음된 오디오 미리듣기 설정
    const audioURL = URL.createObjectURL(blob);
    recordedAudio.src = audioURL;
    recordedAudio.style.display = 'block';
    
    // 녹음된 블롭 저장
    recordedBlob = blob;
    
    // 분석 버튼 활성화
    analyzeButton.disabled = false;
}

/**
 * 녹음된 오디오 분석
 */
function analyzeRecording() {
    // 분석 상태 업데이트
    analysisStatusText.textContent = '분석 중...';
    analysisLoader.classList.add('active');
    
    // 버튼 비활성화
    analyzeButton.disabled = true;
    
    // 폼 데이터 생성
    const formData = new FormData();
    formData.append('audio', recordedBlob, 'recording.wav');
    
    // 서버에 오디오 업로드 및 분석
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 분석 결과 저장
            analysisResult = data.result;
            
            // 분석 상태 업데이트
            analysisStatusText.textContent = '분석 완료';
            analysisLoader.classList.remove('active');
            
            // 결과 표시
            displayAnalysisResult();
        } else {
            throw new Error(data.error || '파일 업로드 중 오류가 발생했습니다.');
        }
    })
    .catch(error => {
        console.error('오류:', error);
        analysisStatusText.textContent = `오류: ${error.message}`;
        analysisLoader.classList.remove('active');
        
        // 분석 버튼 재활성화
        analyzeButton.disabled = false;
    });
}

/**
 * 분석 결과 표시
 */
function displayAnalysisResult() {
    // 결과 섹션 표시
    analysisResultsSection.style.display = 'block';
    
    // 스크롤하여 결과 섹션으로 이동
    analysisResultsSection.scrollIntoView({ behavior: 'smooth' });
    
    // 기본 정보 표시
    wavKeyElement.textContent = analysisResult.wavKey;
    scaleTypeElement.textContent = analysisResult.scaleType;
    
    // 통합된 세그먼트 정보 표시
    displayConsolidatedSegments();
    
    // 차트 시각화 (원본 세그먼트 데이터 사용)
    createVisualizationChart();
}

/**
 * 통합된 세그먼트 목록 표시
 */
function displayConsolidatedSegments() {
    segmentsListElement.innerHTML = '';
    
    // 통합된 세그먼트가 없는 경우
    if (!analysisResult.consolidatedSegments || analysisResult.consolidatedSegments.length === 0) {
        segmentsListElement.innerHTML = '<p>분석된 세그먼트가 없습니다.</p>';
        return;
    }
    
    // 각 통합 세그먼트 그룹 표시
    analysisResult.consolidatedSegments.forEach(group => {
        const groupContainer = document.createElement('div');
        groupContainer.classList.add('segment-group');
        
        // 그룹 헤더 생성
        const groupHeader = document.createElement('div');
        groupHeader.classList.add('segment-group-header');
        groupHeader.textContent = `${group.startTimeSec.toFixed(2)}초 ~ ${group.endTimeSec.toFixed(2)}초`;
        
        groupContainer.appendChild(groupHeader);
        
        // 그룹 내용 생성
        const groupContent = document.createElement('div');
        groupContent.classList.add('segment-content');
        
        // 피드백 및 특성 정보 표시
        groupContent.innerHTML = `
            <div class="feedback-section">
                <p>${group.feedback}</p>
            </div>
            <div class="segment-details">
                <div class="segment-detail">
                    <div class="detail-label">성대 진동</div>
                    <div class="detail-value">${group.vocalCord}</div>
                </div>
                <div class="segment-detail">
                    <div class="detail-label">접촉</div>
                    <div class="detail-value">${group.contact}</div>
                </div>
                <div class="segment-detail">
                    <div class="detail-label">후두 위치</div>
                    <div class="detail-value">${group.larynx}</div>
                </div>
                <div class="segment-detail">
                    <div class="detail-label">발성 강도</div>
                    <div class="detail-value">${group.strength}</div>
                </div>
            </div>
            <div class="segment-meta">
                <small>세그먼트 ${group.segmentIndices.join(', ')} 병합</small>
            </div>
        `;
        
        groupContainer.appendChild(groupContent);
        segmentsListElement.appendChild(groupContainer);
    });
}

/**
 * 시각화 차트 생성 - 미세 세그먼트 특화 (0.2초 단위 시각화)
 */
function createVisualizationChart() {
    // 기존 차트가 있으면 파괴
    if (visualizationChart) {
        visualizationChart.destroy();
    }
    
    // 세그먼트가 없는 경우
    if (!analysisResult.segments || analysisResult.segments.length === 0) {
        return;
    }
    
    // 세그먼트를 시간 순으로 정렬
    const sortedSegments = [...analysisResult.segments].sort((a, b) => 
        a.startTimeSec - b.startTimeSec
    );
    
    // 특성 값을 숫자로 변환하는 함수
    function convertToNumber(value) {
        // 예: "L_L" => 1, "L_H" => 2, "M_L" => 3, "M_H" => 4, "H_L" => 5, "H_H" => 6
        const valueMap = {
            "L_L": 1, "L_H": 2,
            "M_L": 3, "M_H": 4,
            "H_L": 5, "H_H": 6
        };
        
        return valueMap[value] || 0;
    }
    
    // 차트 데이터 준비
    const labels = sortedSegments.map(segment => `${segment.startTimeSec.toFixed(2)}s`);
    
    // 데이터셋 준비
    const datasets = [
        {
            label: '성대 진동',
            data: sortedSegments.map(segment => convertToNumber(segment.vocalCord)),
            backgroundColor: 'rgba(255, 99, 132, 0.5)',
            borderColor: 'rgba(255, 99, 132, 1)',
            borderWidth: 1
        },
        {
            label: '접촉',
            data: sortedSegments.map(segment => convertToNumber(segment.contact)),
            backgroundColor: 'rgba(54, 162, 235, 0.5)',
            borderColor: 'rgba(54, 162, 235, 1)',
            borderWidth: 1
        },
        {
            label: '후두 위치',
            data: sortedSegments.map(segment => convertToNumber(segment.larynx)),
            backgroundColor: 'rgba(255, 206, 86, 0.5)',
            borderColor: 'rgba(255, 206, 86, 1)',
            borderWidth: 1
        },
        {
            label: '발성 강도',
            data: sortedSegments.map(segment => convertToNumber(segment.strength)),
            backgroundColor: 'rgba(75, 192, 192, 0.5)',
            borderColor: 'rgba(75, 192, 192, 1)',
            borderWidth: 1
        }
    ];
    
    // Chart.js를 사용하여 차트 생성
    visualizationChart = new Chart(visualizationChartElement, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 6,
                    ticks: {
                        stepSize: 1,
                        callback: function(value) {
                            const labels = ['', 'L_L', 'L_H', 'M_L', 'M_H', 'H_L', 'H_H'];
                            return labels[value] || '';
                        }
                    }
                },
                x: {
                    // 시간 축은 표시할 때 8개 정도만 표시하여 복잡하지 않게
                    ticks: {
                        maxTicksLimit: 8,
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const valueLabels = ['', 'L_L', 'L_H', 'M_L', 'M_H', 'H_L', 'H_H'];
                            const value = context.raw;
                            return `${context.dataset.label}: ${valueLabels[value] || '알 수 없음'}`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * 스케일 선택 처리
 * @param {Event} event - 클릭 이벤트
 */
function handleScaleSelection(event) {
    // 이전 선택 항목 초기화
    const previousSelected = document.querySelector('.scale-item.selected');
    if (previousSelected) {
        previousSelected.classList.remove('selected');
    }
    
    // 현재 항목 선택
    const scaleItem = event.currentTarget;
    scaleItem.classList.add('selected');
    
    // 스케일 정보 업데이트
    selectedScale = {
        name: scaleItem.dataset.name,
        path: scaleItem.dataset.path
    };
    
    // 오디오 플레이어 업데이트
    scalePlayer.src = `/static/${selectedScale.path}`;
    selectedScaleText.textContent = selectedScale.name;
    
    // 버튼 활성화
    playScaleButton.disabled = false;
    startRecordingButton.disabled = false;
}
