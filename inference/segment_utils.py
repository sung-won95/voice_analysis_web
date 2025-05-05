"""
세그먼트 처리 유틸리티 함수
"""
import os
from inference.speech_analysis_model import generate_segment_feedback

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
            "strength": "M_H",
            "pitch": 130.5
        },
        {
            "segmentIndex": 2,
            "startTimeSec": 1.2,
            "endTimeSec": 1.4,
            "vocalCord": "M_L",
            "contact": "H_L",
            "larynx": "M_M",
            "strength": "M_H",
            "pitch": 135.8
        },
        {
            "segmentIndex": 3,
            "startTimeSec": 1.4,
            "endTimeSec": 1.6,
            "vocalCord": "M_H",
            "contact": "M_L",
            "larynx": "M_H",
            "strength": "M_L",
            "pitch": 220.3
        },
        {
            "segmentIndex": 4,
            "startTimeSec": 1.6,
            "endTimeSec": 1.8,
            "vocalCord": "M_H",
            "contact": "M_L",
            "larynx": "M_H",
            "strength": "M_L",
            "pitch": 245.2
        },
        {
            "segmentIndex": 5,
            "startTimeSec": 1.8,
            "endTimeSec": 2.0,
            "vocalCord": "M_H",
            "contact": "M_L",
            "larynx": "H_L",
            "strength": "M_L",
            "pitch": 360.7
        },
        {
            "segmentIndex": 6,
            "startTimeSec": 2.0,
            "endTimeSec": 2.2,
            "vocalCord": "M_L",
            "contact": "H_L",
            "larynx": "M_M",
            "strength": "M_H",
            "pitch": 450.1
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
            "feedback": "후두의 급격한 변화가 관찰됩니다. 더 안정적인 발성이 필요합니다."
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
    
    # 피치별 그룹화 테스트 데이터
    from inference.pitch_analysis import group_segments_by_pitch  # 이 함수가 실제로 구현되어 있어야 함
    pitch_groups = [
        {
            "pitchGroup": "낮은 음역",
            "avgPitch": 133.2,
            "startTimeSec": 1.0,
            "endTimeSec": 1.4,
            "segmentCount": 2,
            "vocalCord": "M_L",
            "contact": "H_L",
            "larynx": "M_M",
            "strength": "M_H",
            "feedback": "낮은 음역에서는 성대가 중간 정도 두께로 진동하며, 성대 접촉이 강하나 약간 느슨합니다. 후두 위치가 적절합니다. 발성 강도가 적절하나 약간 강합니다. 이 낮은 음역대에서는 성대 접촉을 적절히 유지하면서 후두를 이완시키는 것이 도움이 됩니다.",
            "segmentIndices": [1, 2]
        },
        {
            "pitchGroup": "중간 음역",
            "avgPitch": 232.8,
            "startTimeSec": 1.4,
            "endTimeSec": 1.8,
            "segmentCount": 2,
            "vocalCord": "M_H",
            "contact": "M_L",
            "larynx": "M_H",
            "strength": "M_L",
            "feedback": "중간 음역에서는 성대가 적절한 두께로 강하게 진동합니다. 성대 접촉이 적절하나 약간 부족합니다. 후두 위치가 적절하나 약간 높습니다. 발성 강도가 적절하나 약간 부족합니다. 이 중간 음역대에서는 균형 잡힌 발성이 중요하며, 과도한 힘을 빼고 자연스럽게 발성하세요.",
            "segmentIndices": [3, 4]
        },
        {
            "pitchGroup": "중상 음역",
            "avgPitch": 360.7,
            "startTimeSec": 1.8,
            "endTimeSec": 2.0,
            "segmentCount": 1,
            "vocalCord": "M_H",
            "contact": "M_L",
            "larynx": "H_L",
            "strength": "M_L",
            "feedback": "중상 음역에서는 성대가 적절한 두께로 강하게 진동합니다. 성대 접촉이 적절하나 약간 부족합니다. 후두 위치가 높으나 약간 이완되어 있습니다. 발성 강도가 적절하나 약간 부족합니다. 이 중상 음역대에서는 성대가 너무 얇아지지 않도록 하면서 후두 긴장을 조절하세요.",
            "segmentIndices": [5]
        },
        {
            "pitchGroup": "높은 음역",
            "avgPitch": 450.1,
            "startTimeSec": 2.0,
            "endTimeSec": 2.2,
            "segmentCount": 1,
            "vocalCord": "M_L",
            "contact": "H_L",
            "larynx": "M_M",
            "strength": "M_H",
            "feedback": "높은 음역에서는 성대가 적절한 두께로 진동하나 약간 부족합니다. 성대 접촉이 강하나 약간 느슨합니다. 후두 위치가 적절합니다. 발성 강도가 적절하나 약간 강합니다. 이 높은 음역대에서는 후두가 과도하게 상승하지 않도록 주의하면서 성대 접촉을 유지하세요.",
            "segmentIndices": [6]
        }
    ]
    
    # 결과 JSON 구성
    result = {
        "wavKey": os.path.basename(wav_path),
        "scaleType": feedback,
        "segments": raw_segments,  # 원시 세그먼트 데이터
        "consolidatedSegments": consolidated_segments,  # 통합된 세그먼트
        "pitchGroups": pitch_groups  # 피치별 그룹화 결과 (새로 추가)
    }
    
    return result