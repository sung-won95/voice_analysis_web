/**
 * 스케일 관리 JavaScript 파일
 * 5도 스케일 목록을 로드하고 표시합니다.
 */

/**
 * 서버에서 스케일 목록 로드
 */
function loadScales() {
    fetch('/scales')
        .then(response => response.json())
        .then(scales => {
            // 스케일 목록이 비어있는 경우
            if (scales.length === 0) {
                addDefaultScales();
                return;
            }
            
            // 스케일 목록 표시
            displayScales(scales);
        })
        .catch(error => {
            console.error('스케일 목록 로드 중 오류:', error);
            // 오류 발생 시 기본 스케일 추가
            addDefaultScales();
        });
}

/**
 * 기본 스케일 추가 (서버에 스케일 파일이 없는 경우)
 */
function addDefaultScales() {
    const defaultScales = [
        { name: 'C 5도 스케일', path: 'scales/c_scale.wav' },
        { name: 'D 5도 스케일', path: 'scales/d_scale.wav' },
        { name: 'E 5도 스케일', path: 'scales/e_scale.wav' },
        { name: 'F 5도 스케일', path: 'scales/f_scale.wav' },
        { name: 'G 5도 스케일', path: 'scales/g_scale.wav' },
        { name: 'A 5도 스케일', path: 'scales/a_scale.wav' },
        { name: 'B 5도 스케일', path: 'scales/b_scale.wav' }
    ];
    
    displayScales(defaultScales);
    
    // 서버에 스케일 폴더가 없을 수 있음을 알림
    const scaleList = document.getElementById('scale-list');
    const warningDiv = document.createElement('div');
    warningDiv.classList.add('warning');
    warningDiv.innerHTML = `
        <p>⚠️ 스케일 파일이 서버에 없습니다. 'static/scales' 폴더에 스케일 오디오 파일을 추가하세요.</p>
    `;
    scaleList.parentNode.insertBefore(warningDiv, scaleList.nextSibling);
}

/**
 * 스케일 목록 화면에 표시
 * @param {Array} scales - 스케일 목록
 */
function displayScales(scales) {
    const scaleList = document.getElementById('scale-list');
    scaleList.innerHTML = '';
    
    scales.forEach(scale => {
        const scaleItem = document.createElement('div');
        scaleItem.classList.add('scale-item');
        scaleItem.dataset.name = scale.name;
        scaleItem.dataset.path = scale.path;
        scaleItem.textContent = scale.name;
        
        // 클릭 이벤트 등록
        scaleItem.addEventListener('click', handleScaleSelection);
        
        scaleList.appendChild(scaleItem);
    });
}
