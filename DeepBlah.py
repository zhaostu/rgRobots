import rg
import random

NOT_ALLOWED = ('invalid', 'obstacle')

ENCOURAGE = 0.05
COLLISION_DAMAGE = rg.settings.collision_damage
ATTACK_DAMAGE = sum(rg.settings.attack_range) / 2.0
SUICIDE_DAMAGE = rg.settings.suicide_damage

# Use DFS to find distance to get out of spawn for each spawn point.
SPAWN_COORDS = {}

def distance_out(loc):
    if loc in SPAWN_COORDS:
        return SPAWN_COORDS[loc]

    SPAWN_COORDS[loc] = dist = 99

    for l in rg.locs_around(loc, filter_out=NOT_ALLOWED):
        if l not in rg.settings.spawn_coords:
            SPAWN_COORDS[loc] = 1
            return 1
        else:
            dist = min(dist, distance_out(l) + 1)

    SPAWN_COORDS[loc] = dist
    return dist

for loc in rg.settings.spawn_coords:
    distance_out(loc)

current_actions = {}
current_turn = 0

class Evaluation(object):
    hp = None
    def __init__(self, terrible=False):
        self.terrible = terrible
        self.kills_made = 0
        self.damage_made = 0
        self.damage_taken = 0
        self.tweak = 0

    def __cmp__(self, other):
        if self.terrible != other.terrible:
            return -1 if self.terrible else 1

        self_die = self.damage_taken >= self.hp
        other_die = other.damage_taken >= self.hp

        if self_die != other_die:
            return -1 if self_die else 1

        if self.kills_made != other.kills_made:
            return self.kills_made - other.kills_made

        self_damage_diff = self.damage_made - self.damage_taken
        other_damage_diff = other.damage_made - other.damage_taken
        if self_damage_diff != other_damage_diff:
            return self_damage_diff - other_damage_diff

        if self.tweak != other.tweak:
            return 1 if self.tweak > other.tweak else -1
        else:
            return 0

    def __str__(self):
        return '<Evaluation: t={},km={},dm={},dt={},tk={}>'.format(
                self.terrible,
                self.kills_made,
                self.damage_made,
                self.damage_taken,
                self.tweak)

class Robot(object):
    game = None
    def act(self, game):
        Robot.game = game
        Evaluation.hp = self.hp

        # Clear current_actions
        if game.turn != current_turn:
            current_actions = {}

        best_actions = []
        best_score = Evaluation()
        best_score.terrible = True
        for action, score in self.gen_actions():
            if score > best_score:
                best_actions = [action]
                best_score = score
            elif score == best_score:
                best_actions.append(action)
        action = random.choice(best_actions)
        current_actions[self.location] = action
        return action

    def gen_actions(self):
        ''' A generator that gens all valid moves and its score. '''
        for loc in rg.locs_around(self.location, filter_out=NOT_ALLOWED):
            yield (('move', loc), self.eval_move(loc))
            yield (('attack', loc), self.eval_attack(loc))

        yield (('guard',), self.eval_guard())
        yield (('suicide',), self.eval_suicide())

    def eval_move(self, loc):
        return self.eval_square(loc, move=True)

    def eval_attack(self, loc):
        score = self.eval_square(self.location)

        r = Robot.game.robots.get(loc)
        if r is not None:
            if r.player_id != self.player_id:
                if r.hp <= ATTACK_DAMAGE:
                    score.kills_made = 1
                else:
                    score.damage_made = ATTACK_DAMAGE
                return score
            else:
                score.terrible = True

        best_kills_damage = (0, 0)
        for l, r in self.adjacent_robots(loc):
            if r.player_id != self.player_id:
                if r.hp <= ATTACK_DAMAGE:
                    kd = (0.5, 0)
                else:
                    kd = (0, ATTACK_DAMAGE / 2)

                if kd > best_kills_damage:
                    best_kills_damage = kd

        score.kills_made, score.damage_made = best_kills_damage
        return score

    def eval_guard(self):
        score = self.eval_square(self.location)
        score.damage_taken /= 2

        return score

    def eval_suicide(self):
        score = Evaluation()
        score.damage_taken = self.hp
        for l, r in self.adjacent_robots(self.location):
            if r.player_id != self.player_id:
                if r.hp <= SUICIDE_DAMAGE:
                    score.kills_made += 1
                else:
                    score.damage_made += SUICIDE_DAMAGE

        return score

    def eval_square(self, loc, move=False):
        score = Evaluation()
        # Evaluate whether the bot can get out of the spawn point.
        if loc in SPAWN_COORDS:
            next_spawn = self.next_spawn()
            if next_spawn <= SPAWN_COORDS[loc]:
                # Stuck in spawn point, bot will be lost.
                score.damage_taken = self.hp
            else:
                # Discourage from stay in spawn points.
                score.tweak -= ENCOURAGE * SPAWN_COORDS[loc]

        # Evaluate the damages that will be taken by other bots (including
        # collisions).
        for l, r in self.adjacent_robots(loc):
            if r.player_id != self.player_id:
                if r.hp <= ATTACK_DAMAGE:
                    # The robot might suicide
                    score.damage_taken += SUICIDE_DAMAGE
                else:
                    score.damage_taken += ATTACK_DAMAGE
            elif l in current_actions and current_actions[l][0] == 'move' \
                    and current_actions[l][1] == loc:
                # Should not move into an ally bot.
                score.terrible = True

        if move:
            # Evaluate whether collision can happen.
            r = Robot.game.robots.get(loc)
            if r is not None and r.get('robot_id') != self.robot_id:
                if r.player_id != self.player_id:
                    score.damage_taken += ATTACK_DAMAGE
                elif loc not in current_actions or current_actions[loc][0] == 'move':
                    score.terrible = True

        score.tweak += self.strategy_tweak(loc)
        return score

    def strategy_tweak(self, loc):
        tweak = 0
        # Better to be certain distance from the center.
        tweak -= abs(rg.wdist(loc, rg.CENTER_POINT) - 6) * ENCOURAGE

        # TODO: Better to be close to allies.
        return tweak

    def next_spawn(self):
        return rg.settings.spawn_every - Robot.game.turn % rg.settings.spawn_every

    def adjacent_robots(self, loc):
        ''' A generator that returns all robots adjacent to the location that
            is not self. '''
        for l in rg.locs_around(loc, filter_out=NOT_ALLOWED):
            r = Robot.game.robots.get(l)
            if r is not None and r.get('robot_id') != self.robot_id:
                yield l, r
