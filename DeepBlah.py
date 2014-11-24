import rg
import random

NOT_ALLOWED = ('invalid', 'obstacle')

TERRIBLE = -99
ENCOURAGE = 0.05
COLLISION_DAMAGE = rg.settings.collision_damage
ATTACK_DAMAGE = sum(rg.settings.attack_range) / 2.0
SUICIDE_DAMAGE = rg.settings.suicide_damage

class Robot(object):
    current_moves = {}
    current_turn = 0

    def act(self, game):
        best_actions = []
        best_score = -99999
        for action, score in self.gen_actions(game):
            if score > best_score:
                best_actions = [action]
                best_score = score
            elif score == best_score:
                best_actions.append(action)

        return random.choice(best_actions)

    def gen_actions(self, game):
        ''' A generator that gens all valid moves and its score. '''
        for loc in rg.locs_around(self.location, filter_out=NOT_ALLOWED):
            yield (['move', loc], self.eval_move(loc, game))
            yield (['attack', loc], self.eval_attack(loc, game))

        yield (['guard'], self.eval_guard(game))
        yield (['suicide'], self.eval_suicide(game))

    def eval_move(self, loc, game):
        score = self.eval_square(loc, game)
        return score + self.strategy_tweak(loc, game)

    def eval_attack(self, loc, game):
        score = self.eval_square(self.location, game)

        r = game.robots.get(loc)
        if r is not None:
            if r.player_id != self.player_id:
                score += ATTACK_DAMAGE

        for r in self.adjacent_robots(loc, game):
            if r.player_id != self.player_id:
                score += ATTACK_DAMAGE / 3.01
        return score + self.strategy_tweak(self.location, game)

    def eval_guard(self, game):
        score = self.eval_square(self.location, game)
        if score != TERRIBLE:
            score /= 2.0

        return score + self.strategy_tweak(self.location, game)

    def eval_suicide(self, game):
        score = -self.hp
        for r in self.adjacent_robots(self.location, game):
            if r.player_id != self.player_id:
                score += min(r.hp, SUICIDE_DAMAGE) / 2.0

        return score

    def eval_square(self, loc, game):
        score = 0
        # Terrible if there will be spawn next round.
        if "spawn" in rg.loc_types(loc):
            next_spawn = self.next_spawn(game)
            if next_spawn == 0:
                return TERRIBLE
            else:
                score -= ENCOURAGE * next_spawn

        # TODO: check whether any ally robots is going to move/leave there.
        # If any robot is already there.
        r = game.robots.get(loc)
        if r is not None and r.get('robot_id') != self.robot_id:
            if r.player_id != self.player_id:
                score -= ATTACK_DAMAGE
            else:
                score -= COLLISION_DAMAGE

        # If any robot is next to it.
        for r in self.adjacent_robots(loc, game):
            if r.player_id != self.player_id:
                score -= ATTACK_DAMAGE
            else:
                score -= COLLISION_DAMAGE

        return score

    def strategy_tweak(self, loc, game):
        tweak = 0
        # Better to be close to the center.
        tweak -= rg.wdist(loc, rg.CENTER_POINT) * ENCOURAGE

        # TODO: Better to be close to allies.
        return tweak

    def next_spawn(self, game):
        return game.turn % rg.settings.spawn_every

    def adjacent_robots(self, loc, game):
        ''' A generator that returns all robots adjacent to the location that
            is not self. '''
        for l in rg.locs_around(loc, filter_out=NOT_ALLOWED):
            r = game.robots.get(l)
            if r is not None and r.get('robot_id') != self.robot_id:
                yield r
