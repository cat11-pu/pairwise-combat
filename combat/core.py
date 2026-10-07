"""回合制战斗结算内核，只依赖 Python 标准库。

战斗单位（Combatant）携带生命、攻击、护甲、抗性、暴击、护盾与持续伤害
状态：一次普通攻击依次经过暴击判定、护甲减伤、抗性减伤、伤害下限与护盾
吸收，最后落在生命上；治疗先补足生命，剩下的部分转为护盾；每个回合结束
时按登记顺序为每个单位结算持续伤害。

随机性只来自 Combat(seed=...) 注入的种子，同一个 seed 加同一串调用得到
完全相同的结果。内核不做任何 I/O，也不使用模块级的全局随机源。
"""

import random

#: 单次命中的伤害下限。
MIN_DAMAGE = 1.0

#: 护盾上限比例。
SHIELD_RATIO = 0.3


def clamp(value, low, high):
    """把 value 限制在 [low, high] 区间内。"""
    if value < low:
        return low
    if value > high:
        return high
    return value


def armor_multiplier(armor):
    """护甲减伤系数：100 点护甲把伤害减半。"""
    return 100.0 / (100.0 + armor)


def resist_multiplier(resist):
    """抗性减伤系数：抗性最多减免四分之三的伤害。"""
    return 1.0 - min(resist, 0.75)


class DotEffect:
    """一段持续伤害：每回合结束时结算一次。"""

    def __init__(self, damage, turns):
        self.damage = float(damage)
        self.turns = int(turns)

    def __repr__(self):
        return "DotEffect(damage=%r, turns=%r)" % (self.damage, self.turns)


class Combatant:
    """一个战斗单位：hp 是当前生命，max_hp 缺省与 hp 相同。"""

    def __init__(self, name, hp, attack, armor=0.0, resist=0.0,
                 crit_chance=0.0, crit_multiplier=2.0, max_hp=None):
        self.name = name
        self.max_hp = float(hp if max_hp is None else max_hp)
        self.hp = clamp(float(hp), 0.0, self.max_hp)
        self.attack = float(attack)
        self.armor = float(armor)
        self.resist = float(resist)
        self.crit_chance = clamp(float(crit_chance), 0.0, 1.0)
        self.crit_multiplier = float(crit_multiplier)
        self.shield = 0.0
        self.dots = []

    @property
    def alive(self):
        return self.hp > 0.0

    def missing_hp(self):
        """距离满血还差多少点。"""
        return max(0.0, self.max_hp - self.hp)

    def shield_cap(self):
        return self.max_hp * SHIELD_RATIO


class Combat:
    """一场战斗：按调用顺序结算，结果写进 log。"""

    def __init__(self, seed=0):
        self.rng = random.Random(seed)
        self.round = 0
        self.units = []
        self.log = []

    def register(self, *units):
        """把单位登记进战斗，登记顺序决定回合末的结算顺序。"""
        self.units.extend(units)
        return units

    def resolve_damage(self, attacker, defender):
        """结算一次命中，返回这一次命中的伤害。"""
        crit = self.rng.random() < attacker.crit_chance
        raw = attacker.attack
        if crit:
            raw = raw * attacker.crit_multiplier
        damage = raw * armor_multiplier(defender.armor)
        damage = damage * resist_multiplier(defender.resist)
        damage = max(MIN_DAMAGE, damage)
        absorbed = min(defender.shield, damage)
        defender.shield -= absorbed
        defender.hp = max(0.0, defender.hp - (damage - absorbed))
        self.log.append({
            "round": self.round,
            "kind": "attack",
            "source": attacker.name,
            "target": defender.name,
            "crit": crit,
            "damage": damage,
        })
        return damage

    def attack(self, attacker, defender):
        """一次普通攻击；对已阵亡的目标不再结算。"""
        if not defender.alive:
            return 0.0
        return self.resolve_damage(attacker, defender)

    def heal(self, target, amount):
        """治疗：先补生命，溢出转护盾；返回补到生命的点数。"""
        if not target.alive:
            return 0.0
        amount = max(0.0, float(amount))
        restored = min(amount, target.missing_hp())
        target.hp += restored
        overflow = amount - restored
        if overflow > 0.0:
            target.shield = min(target.shield_cap(), target.shield + overflow)
        self.log.append({
            "round": self.round,
            "kind": "heal",
            "target": target.name,
            "restored": restored,
        })
        return restored

    def apply_shield(self, target, amount):
        """给目标加上护盾，返回加完之后的护盾值。"""
        amount = max(0.0, float(amount))
        target.shield = min(target.shield_cap(), target.shield + amount)
        self.log.append({
            "round": self.round,
            "kind": "shield",
            "target": target.name,
            "shield": target.shield,
        })
        return target.shield

    def apply_dot(self, target, damage, turns):
        """给目标挂上一段持续伤害。"""
        effect = DotEffect(damage, turns)
        target.dots.append(effect)
        self.log.append({
            "round": self.round,
            "kind": "dot",
            "target": target.name,
            "damage": effect.damage,
            "turns": effect.turns,
        })
        return effect

    def end_turn(self):
        """回合末结算：按登记顺序为每个单位结算持续伤害。"""
        self.round += 1
        events = []
        for unit in self.units:
            for effect in list(unit.dots):
                self._tick_dot(unit, effect)
                events.append((unit.name, effect.damage))
            unit.dots = [effect for effect in unit.dots if effect.turns > 0]
        return events

    def _tick_dot(self, unit, effect):
        """结算一段持续伤害。"""
        damage = effect.damage
        absorbed = min(unit.shield, damage)
        unit.shield -= absorbed
        unit.hp = max(0.0, unit.hp - (damage - absorbed))
        effect.turns -= 1
        self.log.append({
            "round": self.round,
            "kind": "tick",
            "target": unit.name,
            "damage": damage,
        })
