"""
피치 분석 관련 함수
"""
import numpy as np
from collections import defaultdict

def group_segments_by_pitch(segments):
    """
    세그먼트를 피치별로 그룹화하고 평균값을 계산
    
    Parameters:
    -----------
    segments : list
        분석된 세그먼트 목록
    
    Returns:
    --------
    list
        피치 그룹별 평균 분석 결과
    """
    if not segments:
        return []
    
    # 피치 범위 정의 (Hz)
    # 여성 음역대: 약 160-1200 Hz, 남성 음역대: 약 85-500 Hz
    # 7개 그룹으로 나눔 (낮은 음부터 높은 음까지)
    pitch_ranges = [
        {"name": "매우 낮은 음역", "min": 80, "max": 130},
        {"name": "낮은 음역", "min": 130, "max": 180},
        {"name": "중하 음역", "min": 180, "max": 240},
        {"name": "중간 음역", "min": 240, "max": 300},
        {"name": "중상 음역", "min": 300, "max": 400},
        {"name": "높은 음역", "min": 400, "max": 600},
        {"name": "매우 높은 음역", "min": 600, "max": 1200}
    ]
    
    # 피치 그룹별 세그먼트 분류
    pitch_groups_data = defaultdict(list)
    
    for segment in segments:
        if "pitch" not in segment:
            continue
            
        pitch = segment["pitch"]
        group_found = False
        
        for pitch_range in pitch_ranges:
            if pitch_range["min"] <= pitch < pitch_range["max"]:
                pitch_groups_data[pitch_range["name"]].append(segment)
                group_found = True
                break
        
        # 범위를 벗어나는 경우
        if not group_found:
            if pitch < pitch_ranges[0]["min"]:
                pitch_groups_data[pitch_ranges[0]["name"]].append(segment)
            elif pitch >= pitch_ranges[-1]["max"]:
                pitch_groups_data[pitch_ranges[-1]["name"]].append(segment)
    
    # 각 그룹별 평균 계산
    pitch_groups = []
    
    # 속성별 코드와 점수 매핑
    attribute_mapping = {
        "vocalCord": {"L_L": 1, "L_M": 2, "L_H": 3, "M_L": 4, "M_M": 5, "M_H": 6, "H_L": 7, "H_M": 8, "H_H": 9},
        "contact": {"L_L": 1, "L_M": 2, "L_H": 3, "M_L": 4, "M_M": 5, "M_H": 6, "H_L": 7, "H_M": 8, "H_H": 9},
        "larynx": {"L_L": 1, "L_M": 2, "L_H": 3, "M_L": 4, "M_M": 5, "M_H": 6, "H_L": 7, "H_M": 8, "H_H": 9},
        "strength": {"L_L": 1, "L_M": 2, "L_H": 3, "M_L": 4, "M_M": 5, "M_H": 6, "H_L": 7, "H_M": 8, "H_H": 9}
    }
    
    # 점수에서 코드로 변환하는 함수
    def score_to_code(attribute, score):
        for code, value in attribute_mapping[attribute].items():
            if value == score:
                return code
        # 기본값 반환
        return "M_M"
    
    for group_name, group_segments in pitch_groups_data.items():
        if not group_segments:
            continue
            
        # 평균 피치 계산
        avg_pitch = np.mean([s["pitch"] for s in group_segments if "pitch" in s])
        
        # 각 속성의 평균 점수 계산
        attributes = {"vocalCord": [], "contact": [], "larynx": [], "strength": []}
        
        for segment in group_segments:
            for attr, attr_name in zip(
                ["vocalCord", "contact", "larynx", "strength"],
                ["vocal_cord", "contact", "larynx", "strength"]
            ):
                attr_key = attr  # JSON에서 사용하는 키
                if attr_key in segment and segment[attr_key] in attribute_mapping[attr]:
                    attributes[attr].append(attribute_mapping[attr][segment[attr_key]])
        
        # 평균 점수 계산 및 코드로 변환
        avg_attributes = {}
        for attr, scores in attributes.items():
            if scores:
                avg_score = round(np.mean(scores))
                avg_attributes[attr] = score_to_code(attr, avg_score)
            else:
                avg_attributes[attr] = "M_M"  # 기본값
        
        # 시간 범위 계산
        start_times = [s["startTimeSec"] for s in group_segments]
        end_times = [s["endTimeSec"] for s in group_segments]
        
        # 해당 피치 그룹에 대한 피드백 생성
        group_feedback = generate_pitch_group_feedback(group_name, avg_attributes)
        
        # 그룹 정보 저장
        group_info = {
            "pitchGroup": group_name,
            "avgPitch": float(f"{avg_pitch:.2f}"),
            "startTimeSec": float(f"{min(start_times):.2f}") if start_times else 0.0,
            "endTimeSec": float(f"{max(end_times):.2f}") if end_times else 0.0,
            "segmentCount": len(group_segments),
            "vocalCord": avg_attributes["vocalCord"],
            "contact": avg_attributes["contact"],
            "larynx": avg_attributes["larynx"],
            "strength": avg_attributes["strength"],
            "feedback": group_feedback,
            "segmentIndices": [s["segmentIndex"] for s in group_segments]
        }
        
        pitch_groups.append(group_info)
    
    # 피치가 낮은 순으로 정렬
    pitch_groups.sort(key=lambda x: x["avgPitch"])
    
    return pitch_groups

def generate_pitch_group_feedback(group_name, attributes):
    """
    피치 그룹별 피드백 생성
    
    Parameters:
    -----------
    group_name : str
        피치 그룹 이름
    attributes : dict
        평균 속성 값
    
    Returns:
    --------
    str
        생성된 피드백
    """
    # 각 속성 코드별 설명
    vocal_cord_feedback = {
        "L_L": "성대가 매우 얇게 진동합니다.",
        "L_M": "성대가 얇게 진동합니다.",
        "L_H": "성대가 얇지만 강하게 진동합니다.",
        "M_L": "성대가 적절한 두께로 진동하나 약간 부족합니다.",
        "M_M": "성대가 적절한 두께로 진동합니다.",
        "M_H": "성대가 적절한 두께로 강하게 진동합니다.",
        "H_L": "성대가 두껍게 진동하나 약간 약합니다.",
        "H_M": "성대가 두껍게 진동합니다.",
        "H_H": "성대가 매우 두껍고 강하게 진동합니다."
    }
    
    contact_feedback = {
        "L_L": "성대 접촉이 매우 약합니다.",
        "L_M": "성대 접촉이 약합니다.",
        "L_H": "성대 접촉이 약하지만 긴장되어 있습니다.",
        "M_L": "성대 접촉이 적절하나 약간 부족합니다.",
        "M_M": "성대 접촉이 적절합니다.",
        "M_H": "성대 접촉이 적절하나 약간 긴장되어 있습니다.",
        "H_L": "성대 접촉이 강하나 약간 느슨합니다.",
        "H_M": "성대 접촉이 강합니다.",
        "H_H": "성대 접촉이 매우 강하고 긴장되어 있습니다."
    }
    
    larynx_feedback = {
        "L_L": "후두 위치가 매우 낮습니다.",
        "L_M": "후두 위치가 낮습니다.",
        "L_H": "후두 위치가 낮고 긴장되어 있습니다.",
        "M_L": "후두 위치가 적절하나 약간 낮습니다.",
        "M_M": "후두 위치가 적절합니다.",
        "M_H": "후두 위치가 적절하나 약간 높습니다.",
        "H_L": "후두 위치가 높으나 약간 이완되어 있습니다.",
        "H_M": "후두 위치가 높습니다.",
        "H_H": "후두 위치가 매우 높고 긴장되어 있습니다."
    }
    
    strength_feedback = {
        "L_L": "발성 강도가 매우 약합니다.",
        "L_M": "발성 강도가 약합니다.",
        "L_H": "발성 강도가 약하지만 힘이 들어갑니다.",
        "M_L": "발성 강도가 적절하나 약간 부족합니다.",
        "M_M": "발성 강도가 적절합니다.",
        "M_H": "발성 강도가 적절하나 약간 강합니다.",
        "H_L": "발성 강도가 강하나 약간 부족한 느낌입니다.",
        "H_M": "발성 강도가 강합니다.",
        "H_H": "발성 강도가 매우 강하고 긴장되어 있습니다."
    }
    
    # 피치 그룹별 기본 피드백
    pitch_group_base_feedback = {
        "매우 낮은 음역": f"{group_name}에서는 ",
        "낮은 음역": f"{group_name}에서는 ",
        "중하 음역": f"{group_name}에서는 ",
        "중간 음역": f"{group_name}에서는 ",
        "중상 음역": f"{group_name}에서는 ",
        "높은 음역": f"{group_name}에서는 ",
        "매우 높은 음역": f"{group_name}에서는 "
    }
    
    # 피드백 생성
    feedback_parts = []
    
    # 기본 피드백으로 시작
    feedback = pitch_group_base_feedback.get(group_name, f"{group_name}에서는 ")
    
    # 각 속성에 대한 피드백 추가
    if attributes.get("vocalCord") in vocal_cord_feedback:
        feedback_parts.append(vocal_cord_feedback[attributes["vocalCord"]])
    
    if attributes.get("contact") in contact_feedback:
        feedback_parts.append(contact_feedback[attributes["contact"]])
    
    if attributes.get("larynx") in larynx_feedback:
        feedback_parts.append(larynx_feedback[attributes["larynx"]])
    
    if attributes.get("strength") in strength_feedback:
        feedback_parts.append(strength_feedback[attributes["strength"]])
    
    # 피드백 조합
    feedback += " ".join(feedback_parts)
    
    # 피치 그룹별 추가 조언
    pitch_advice = {
        "매우 낮은 음역": "이 매우 낮은 음역대에서는 성대를 충분히 두껍게 유지하며 편안하게 발성하는 것이 중요합니다.",
        "낮은 음역": "이 낮은 음역대에서는 성대 접촉을 적절히 유지하면서 후두를 이완시키는 것이 도움이 됩니다.",
        "중하 음역": "이 중하 음역대는 대화에서 자주 사용되는 범위로, 자연스럽고 편안한 발성을 유지하세요.",
        "중간 음역": "이 중간 음역대에서는 균형 잡힌 발성이 중요하며, 과도한 힘을 빼고 자연스럽게 발성하세요.",
        "중상 음역": "이 중상 음역대에서는 성대가 너무 얇아지지 않도록 하면서 후두 긴장을 조절하세요.",
        "높은 음역": "이 높은 음역대에서는 후두가 과도하게 상승하지 않도록 주의하면서 성대 접촉을 유지하세요.",
        "매우 높은 음역": "이 매우 높은 음역대에서는 후두 긴장을 최소화하고 가벼운 발성을 유지하는 것이 중요합니다."
    }
    
    # 추가 조언 추가
    if group_name in pitch_advice:
        feedback += " " + pitch_advice[group_name]
    
    return feedback