import gc
import sys
from dataclasses import dataclass
from typing import List, Any, Dict, Optional

# gc.set_debug(gc.DEBUG_STATS) # 필요시 디버그 정보 활성화
gc.enable()

@dataclass
class Data:
    id: str
    name: str

def get_direct_referring_names(target_obj: Any,
                               current_locals: Optional[Dict[str, Any]] = None,
                               current_globals: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    제공된 로컬 및 전역 스코프, 그리고 gc.get_referrers를 통해 찾은 객체 속성들 중에서
    target_obj를 *직접* 참조하는 변수/속성의 이름을 식별합니다.
    """
    found_names = set()
    
    # 이 함수 내부에서 사용되는 변수 이름이나, 검사 과정에서 일시적으로 target_obj를 담을 수 있는
    # 일반적인 매개변수 이름 등은 최종 결과에서 제외합니다.
    ignore_list_func_internals = {
        'target_obj', 'current_locals', 'current_globals', 'found_names', 
        'name', 'value', 'scope_dict', 'container', 'referrers',
        'var', 'owner_name_str', 'g_name', 'g_val', 'l_name', 'l_val',
        'attr_name', 'attr_value', 'is_explicit_scope_dict'
    }

    # 1. current_locals (현재 함수의 지역 변수) 검사
    if current_locals:
        for name, value in current_locals.items():
            if value is target_obj and name not in ignore_list_func_internals:
                found_names.add(f"{name} (local)")

    # 2. current_globals (전역 변수) 검사
    if current_globals:
        for name, value in current_globals.items():
            if value is target_obj and name not in ignore_list_func_internals:
                found_names.add(f"{name} (global)")
    
    # 3. gc.get_referrers()를 사용하여 다른 객체의 속성 검사
    # 예: some_other_obj.attribute = target_obj 와 같은 경우
    referrers = gc.get_referrers(target_obj)
    for container in referrers:
        if isinstance(container, dict): # 객체의 __dict__는 dict 타입입니다.
            
            # 이 container가 명시적으로 전달된 current_locals나 current_globals 딕셔너리 객체와 동일한지 확인합니다.
            # 동일하다면 이미 위에서 처리했으므로 중복 추가를 방지합니다.
            is_explicit_scope_dict = False
            if current_locals is container:
                is_explicit_scope_dict = True
            if current_globals is container:
                is_explicit_scope_dict = True

            if not is_explicit_scope_dict:
                # 이 container는 다른 객체의 __dict__일 가능성이 높습니다.
                # 이 __dict__를 소유한 객체의 이름을 current_globals나 current_locals에서 찾습니다.
                owner_name_str = None
                
                # 전역에서 소유자 객체 찾기
                if current_globals:
                    for g_name, g_val in current_globals.items():
                        if g_name not in ignore_list_func_internals and hasattr(g_val, '__dict__') and g_val.__dict__ is container:
                            owner_name_str = f"{g_name} (global obj)"
                            break
                
                # 전역에서 못 찾았고, 지역 스코프가 있다면 지역에서 소유자 객체 찾기
                if not owner_name_str and current_locals:
                    for l_name, l_val in current_locals.items():
                         if l_name not in ignore_list_func_internals and hasattr(l_val, '__dict__') and l_val.__dict__ is container:
                            owner_name_str = f"{l_name} (local obj)"
                            break
                
                if owner_name_str:
                    # 소유자 객체를 찾았다면, 이제 이 객체의 어떤 속성이 target_obj를 참조하는지 찾습니다.
                    for attr_name, attr_value in container.items():
                        if attr_value is target_obj and not attr_name.startswith("__") and attr_name not in ignore_list_func_internals:
                            found_names.add(f"{owner_name_str}.{attr_name}")
                # else:
                #   owner_name_str을 찾지 못한 경우, 이 __dict__는 current_locals/globals에서 직접적으로 이름 붙여진 객체의 것이 아니거나
                #   더 복잡한 참조 관계일 수 있습니다. (예: 리스트 안의 객체의 속성 등)
                #   현재는 명시적 스코프 내의 이름있는 객체의 속성에 집중합니다.

    return sorted(list(found_names))


py_obj_data = Data(id = "obj-1", name="obj-1-name")

actual_referrer_global = py_obj_data

def inner(obj_param: Data):
    local_ref_in_inner = obj_param
    print(f"[INNER] py_obj_data를 직접 참조하는 변수들: {get_direct_referring_names(obj_param, locals(), globals())}, 참조 횟수: {sys.getrefcount(obj_param)}")


def inner2(obj_param: Data): 
    local_ref_in_inner2 = obj_param
    print(f"[INNER2] py_obj_data를 직접 참조하는 변수들: {get_direct_referring_names(obj_param, locals(), globals())}, 참조 횟수: {sys.getrefcount(obj_param)}")


gc.collect()
print(f"GC 실행 횟수: {gc.get_count()}")
print(f"객체(py_obj_data)가 GC에 의해 트래킹되고 있는지 여부: {gc.is_tracked(py_obj_data)}")
print(f"[GLOBAL] py_obj_data를 직접 참조하는 변수들: {get_direct_referring_names(py_obj_data, locals(), globals())}, 참조 횟수: {sys.getrefcount(py_obj_data)}")

referrer1_name_val = py_obj_data
print(f"[GLOBAL] py_obj_data를 직접 참조하는 변수들 (referrer1_name_val='{referrer1_name_val}' 할당 후): {get_direct_referring_names(py_obj_data, locals(), globals())}, 참조 횟수: {sys.getrefcount(py_obj_data)}")

# inner 함수 호출 (내부에서 local_ref_in_inner 및 obj_param이 py_obj_data를 참조)
inner(obj_param=py_obj_data)

# inner2 함수 호출 (내부에서 local_ref_in_inner2 및 obj_param이 py_obj_data를 참조)
inner2(obj_param=py_obj_data)

print(f"GC 실행 횟수: {gc.get_count()}")
# 모든 함수 호출 후 전역 상태에서 py_obj_data 참조 확인
print(f"[GLOBAL] py_obj_data를 직접 참조하는 변수들 (모든 함수 호출 후): {get_direct_referring_names(py_obj_data, locals(), globals())}, 참조 횟수: {sys.getrefcount(py_obj_data)}")