/**
 * 피드백 페이지 JavaScript 파일
 * 분석 결과를 표시하고 시각화합니다.
 */

// 분석 결과 데이터
let analysisResult = null;

// DOM 요소
const wavKeyElement = document.getElementById('wav-key');
const scaleTypeElement = document.getElementById('scale-type');
const segmentListElement = document.getElementById('segments-list');
const backToHomeButton = document.getElementById('back-to-home');

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', () => {
    // 세션 스토리지에서 분석 결과 로드
    const storedResult = sessionStorage.getItem('analysisResult');
    
    if (storedResult) {
        analysisResult = JSON.parse(storedResult);
        displayAnalysisResult();
    } else {
        // 분석 결과가 없으면 메시지 표시
        showNoResultMessage();
    }
    
    // 홈으로 돌아가기 버튼 이벤트 등록
    backToHomeButton.addEventListener('click', () => {
        window.location.href = '/';
    });
});

/**
 * 분석 결과 데이터 표시
 */
function displayAnalysisResult() {
    // 기본 정보 표시
    wavKeyElement.textContent = analysisResult.wavKey;
    scaleTypeElement.textContent = analysisResult.scaleType;
    
    // 세그먼트 정보 표시
    displaySegments();
    
    // 차트 시각화
    createVisualizationChart();
}

/**
 * 세그먼트 목록 표시
 */
function displaySegments() {
    segmentListElement.innerHTML = '';
    
    // 세그먼트가 없는 경우
    if (!analysisResult.segments || analysisResult.segments.length === 0) {
        segmentListElement.innerHTML = '<p>분석된 세그먼트가 없습니다.</p>';
        return;
    }
    
    // 세그먼트를 시간 순으로 정렬
    const sortedSegments = [...analysisResult.segments].sort((a, b) => 
        a.startTimeSec - b.startTimeSec
    );
    
    // 각 세그먼트 표시
    sortedSegments.forEach(segment => {
        const segmentItem = document.createElement('div');
        segmentItem.classList.add('segment-item');
        
        segmentItem.innerHTML = `
            <div class="segment-header">
                <span>세그먼트 ${segment.segmentIndex}</span>
                <span>${segment.startTimeSec}초 - ${segment.endTimeSec}초</span>
            </div>
            <div class="segment-details">
                <div class="segment-detail">
                    <div class="detail-label">성대 진동</div>
                    <div class="detail-value">${segment.vocalCord}</div>
                </div>
                <div class="segment-detail">
                    <div class="detail-label">접촉</div>
                    <div class="detail-value">${segment.contact}</div>
                </div>
                <div class="segment-detail">
                    <div class="detail-label">후두 위치</div>
                    <div class="detail-value">${segment.larynx}</div>
                </div>
                <div class="segment-detail">
                    <div class="detail-label">발성 강도</div>
                    <div class="detail-value">${segment.strength}</div>
                </div>
            </div>
        `;
        
        segmentListElement.appendChild(segmentItem);
    });
}

/**
 * 시각화 차트 생성
 */
function createVisualizationChart() {
    const chartElement = document.getElementById('visualization-chart');
    
    // 세그먼트가 없는 경우
    if (!analysisResult.segments || analysisResult.segments.length === 0) {
        chartElement.innerHTML = '<p>차트를 생성할 데이터가 없습니다.</p>';
        return;
    }
    
    // 세그먼트를 시간 순으로 정렬
    const sortedSegments = [...analysisResult.segments].sort((a, b) => 
        a.startTimeSec - b.startTimeSec
    );
    
    // 차트 데이터 준비
    const labels = sortedSegments.map(segment => `${segment.startTimeSec}s-${segment.endTimeSec}s`);
    
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
    
    // 데이터셋 준비
    const datasets = [
        {
            label: '성대 진동',
            data: sortedSegments.map(segment => convertToNumber(segment.vocalCord)),
            borderColor: 'rgba(255, 99, 132, 1)',
            backgroundColor: 'rgba(255, 99, 132, 0.2)',
            borderWidth: 2,
            pointRadius: 4
        },
        {
            label: '접촉',
            data: sortedSegments.map(segment => convertToNumber(segment.contact)),
            borderColor: 'rgba(54, 162, 235, 1)',
            backgroundColor: 'rgba(54, 162, 235, 0.2)',
            borderWidth: 2,
            pointRadius: 4
        },
        {
            label: '후두 위치',
            data: sortedSegments.map(segment => convertToNumber(segment.larynx)),
            borderColor: 'rgba(255, 206, 86, 1)',
            backgroundColor: 'rgba(255, 206, 86, 0.2)',
            borderWidth: 2,
            pointRadius: 4
        },
        {
            label: '발성 강도',
            data: sortedSegments.map(segment => convertToNumber(segment.strength)),
            borderColor: 'rgba(75, 192, 192, 1)',
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            borderWidth: 2,
            pointRadius: 4
        }
    ];
    
    // Chart.js를 사용하여 차트 생성
    new Chart(chartElement, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    angleLines: {
                        display: true
                    },
                    min: 0,
                    max: 6,
                    ticks: {
                        stepSize: 1
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            const valueMap = {
                                1: 'L_L', 2: 'L_H',
                                3: 'M_L', 4: 'M_H',
                                5: 'H_L', 6: 'H_H'
                            };
                            return `${context.dataset.label}: ${valueMap[value] || '알 수 없음'}`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * 분석 결과가 없을 때 메시지 표시
 */
function showNoResultMessage() {
    wavKeyElement.textContent = '분석 결과 없음';
    scaleTypeElement.textContent = '분석 결과가 없습니다. 메인 페이지에서 음성을 녹음하고 분석해주세요.';
    segmentListElement.innerHTML = '<p>분석된 세그먼트가 없습니다.</p>';
    
    document.getElementById('visualization-chart').innerHTML = 
        '<p>차트를 생성할 데이터가 없습니다.</p>';
}
