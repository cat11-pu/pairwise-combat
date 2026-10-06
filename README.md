# combat

一个只依赖 Python 标准库的回合制战斗结算内核。战斗单位带生命、攻击、护甲、
抗性、暴击、护盾与持续伤害状态；普通攻击、治疗、护盾、持续伤害与回合末结算
都在内存里按调用顺序完成，随机性由调用方注入的 seed 决定。

## 目录

- combat/core.py：伤害结算、治疗、护盾、持续伤害与回合末结算
- tests/test_core.py：行为测试

## 跑测试

在项目根目录执行：

    python3 -m unittest discover -s tests -v
