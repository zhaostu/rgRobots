import rg
import random

NOT_ALLOWED = ('invalid', 'obstacle')

TERRIBLE = -99
ENCOURAGE = 0.05
COLLISION_DAMAGE = rg.settings.collision_damage
ATTACK_DAMAGE = sum(rg.settings.attack_range) / 2.0
SUICIDE_DAMAGE = rg.settings.suicide_damage

current_actions = {}
current_turn = 0

class Robot(object):
    game = None
    def act(self, game):
        self.game = game

        # Clear current_actions
        if game.turn != current_turn:
            current_actions = {}

        best_actions = []
        best_score = -99999
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
        score = self.eval_square(loc, move=True)
        return score + self.strategy_tweak(loc)

    def eval_attack(self, loc):
        score = self.eval_square(self.location)

        r = self.game.robots.get(loc)
        if r is not None:
            if r.player_id != self.player_id:
                score += ATTACK_DAMAGE
            else:
                return TERRIBLE

        for l, r in self.adjacent_robots(loc):
            if r.player_id != self.player_id:
                score += ATTACK_DAMAGE / 3.01
        return score + self.strategy_tweak(self.location)

    def eval_guard(self):
        score = self.eval_square(self.location)
        if score > TERRIBLE:
            score /= 2.0

        return score + self.strategy_tweak(self.location)

    def eval_suicide(self):
        score = -self.hp
        for l, r in self.adjacent_robots(self.location):
            if r.player_id != self.player_id:
                score += min(r.hp, SUICIDE_DAMAGE) / 2.0

        return score

    def eval_square(self, loc, move=False):
        score = 0
        # Terrible if there will be spawn next round.
        if "spawn" in rg.loc_types(loc):
            next_spawn = self.next_spawn()
            if next_spawn == 0:
                return TERRIBLE
            else:
                score -= ENCOURAGE * next_spawn

        if move:
            r = self.game.robots.get(loc)
            if r is not None and r.get('robot_id') != self.robot_id:
                if r.player_id != self.player_id:
                    score -= ATTACK_DAMAGE
                elif loc not in current_actions or current_actions[loc][0] == 'move':
                    return TERRIBLE

            # If any robot is next to it.
            for l, r in self.adjacent_robots(loc):
                if r.player_id != self.player_id:
                    score -= ATTACK_DAMAGE
                elif l in current_actions and current_actions[l][0] == 'move' \
                        and current_actions[l][1] == loc:
                    return TERRIBLE

        return score

    def strategy_tweak(self, loc):
        tweak = 0
        # Better to be close to the center.
        tweak -= rg.wdist(loc, rg.CENTER_POINT) * ENCOURAGE

        # TODO: Better to be close to allies.
        return tweak

    def next_spawn(self):
        return self.game.turn % rg.settings.spawn_every

    def adjacent_robots(self, loc):
        ''' A generator that returns all robots adjacent to the location that
            is not self. '''
        for l in rg.locs_around(loc, filter_out=NOT_ALLOWED):
            r = self.game.robots.get(l)
            if r is not None and r.get('robot_id') != self.robot_id:
                yield l, r
