"""Behaviour tests for the turn based combat kernel.

Run them from the project root:

    python3 -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from combat.core import Combat, Combatant


class DamageTest(unittest.TestCase):
    def test_a_full_hit_passes_through_armour_and_resistance(self):
        combat = Combat(seed=3)
        attacker = Combatant("attacker", hp=100, attack=120, crit_chance=0.0)
        defender = Combatant("defender", hp=100, attack=10, armor=100,
                             resist=0.25, max_hp=100)
        combat.register(attacker, defender)
        combat.apply_shield(defender, 20)
        damage = combat.attack(attacker, defender)
        self.assertEqual(damage, 45.0)
        self.assertEqual(defender.shield, 0.0)
        self.assertEqual(defender.hp, 75.0)

    def test_a_certain_critical_hit_doubles_the_attack(self):
        combat = Combat(seed=11)
        attacker = Combatant("attacker", hp=100, attack=30,
                             crit_chance=1.0, crit_multiplier=2.0)
        defender = Combatant("defender", hp=100, attack=10)
        combat.register(attacker, defender)
        self.assertEqual(combat.attack(attacker, defender), 60.0)
        self.assertEqual(defender.hp, 40.0)

    def test_the_same_seed_replays_the_same_fight(self):
        def play():
            combat = Combat(seed=17)
            attacker = Combatant("attacker", hp=200, attack=25, crit_chance=0.5)
            defender = Combatant("defender", hp=200, attack=10)
            combat.register(attacker, defender)
            return [combat.attack(attacker, defender) for _ in range(6)]

        self.assertEqual(play(), play())

    def test_resistance_stops_at_its_ceiling(self):
        combat = Combat(seed=5)
        attacker = Combatant("attacker", hp=100, attack=100, crit_chance=0.0)
        defender = Combatant("defender", hp=100, attack=10, resist=1.0)
        combat.register(attacker, defender)
        damage = combat.attack(attacker, defender)
        self.assertEqual(damage, 25.0)
        self.assertEqual(defender.hp, 75.0)

    def test_a_heavy_armour_target_still_loses_a_minimum_sliver(self):
        combat = Combat(seed=5)
        attacker = Combatant("attacker", hp=100, attack=2, crit_chance=0.0)
        defender = Combatant("defender", hp=100, attack=10, armor=900)
        combat.register(attacker, defender)
        damage = combat.attack(attacker, defender)
        self.assertEqual(damage, 1.0)
        self.assertEqual(defender.hp, 99.0)


class ShieldTest(unittest.TestCase):
    def test_a_shield_absorbs_the_hit_and_never_runs_negative(self):
        combat = Combat(seed=7)
        striker = Combatant("striker", hp=100, attack=8, crit_chance=0.0)
        guard = Combatant("guard", hp=100, attack=10)
        combat.register(striker, guard)
        self.assertEqual(combat.apply_shield(guard, 5), 5.0)
        self.assertEqual(combat.attack(striker, guard), 8.0)
        self.assertEqual(guard.shield, 0.0)
        self.assertEqual(guard.hp, 97.0)
        self.assertEqual(combat.attack(striker, guard), 8.0)
        self.assertEqual(guard.shield, 0.0)
        self.assertEqual(guard.hp, 89.0)

    def test_the_shield_cap_follows_the_maximum_life(self):
        combat = Combat(seed=9)
        striker = Combatant("striker", hp=100, attack=40, crit_chance=0.0)
        veteran = Combatant("veteran", hp=40, attack=10, max_hp=100)
        combat.register(striker, veteran)
        self.assertEqual(combat.apply_shield(veteran, 50), 30.0)
        self.assertEqual(combat.attack(striker, veteran), 40.0)
        self.assertEqual(veteran.shield, 0.0)
        self.assertEqual(veteran.hp, 30.0)


class HealingTest(unittest.TestCase):
    def test_healing_stops_at_full_life_and_the_rest_becomes_shield(self):
        combat = Combat(seed=13)
        medic = Combatant("medic", hp=100, attack=5)
        target = Combatant("target", hp=40, attack=5, max_hp=100)
        combat.register(medic, target)
        self.assertEqual(combat.heal(target, 25), 25.0)
        self.assertEqual(target.hp, 65.0)
        self.assertEqual(combat.heal(target, 80), 35.0)
        self.assertEqual(target.hp, 100.0)
        self.assertEqual(target.shield, 30.0)
        self.assertEqual(combat.apply_shield(target, 100), 30.0)
        self.assertEqual(target.shield, 30.0)


class TurnEndTest(unittest.TestCase):
    def test_dot_ticks_spend_the_shield_and_stop_after_the_duration(self):
        combat = Combat(seed=1)
        unit = Combatant("unit", hp=100, attack=5)
        combat.register(unit)
        combat.apply_shield(unit, 10)
        combat.apply_dot(unit, 6, 2)
        events = combat.end_turn()
        self.assertEqual(events, [("unit", 6.0)])
        self.assertEqual(unit.hp, 100.0)
        self.assertEqual(unit.shield, 4.0)
        events = combat.end_turn()
        self.assertEqual(events, [("unit", 6.0)])
        self.assertEqual(unit.hp, 98.0)
        self.assertEqual(unit.shield, 0.0)
        self.assertEqual(unit.dots, [])
        events = combat.end_turn()
        self.assertEqual(events, [])
        self.assertEqual(unit.hp, 98.0)


class DeathTest(unittest.TestCase):
    def test_a_unit_at_zero_life_is_out_of_the_fight(self):
        combat = Combat(seed=21)
        striker = Combatant("striker", hp=100, attack=2, crit_chance=0.0)
        victim = Combatant("victim", hp=3, attack=1, armor=900)
        combat.register(striker, victim)
        for _ in range(3):
            combat.attack(striker, victim)
        self.assertEqual(victim.hp, 0.0)
        self.assertFalse(victim.alive)
        self.assertEqual(combat.attack(striker, victim), 0.0)
        self.assertEqual(combat.heal(victim, 50), 0.0)
        self.assertEqual(victim.hp, 0.0)


if __name__ == "__main__":
    unittest.main()
