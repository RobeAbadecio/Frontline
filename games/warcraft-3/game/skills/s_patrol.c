#include "s_skills.h"

/* The leg's destination as a fresh waypoint when the current one was recycled (or is missing). */
static edict_t *patrol_destination(edict_t *ent) {
    vec2_t const *point = ent->orders->patrol_to_b ? &ent->orders->patrol_point_b : &ent->orders->patrol_point_a;
    edict_t *target = ent->orders->patrol_target;
    /* Orders from saves that predate the stored endpoints keep their waypoint. */
    bool const legacy = !ent->orders->patrol_point_a.x && !ent->orders->patrol_point_a.y &&
                        !ent->orders->patrol_point_b.x && !ent->orders->patrol_point_b.y;
    if (legacy && target) return target;
    if (!target || fabsf(target->s.origin.x - point->x) > 1.0f || fabsf(target->s.origin.y - point->y) > 1.0f)
        target = ent->orders->patrol_target = Waypoint_add(point);
    return target;
}

static void ai_patrol_walk(edict_t *ent) {
    /* Frontline patrols keep to their route: warships fire on the move (Fuwf) and never
     * break off; other units engage only what is already in weapon range and do not chase
     * (Hold for the fight), then resume the route. */
    bool const route_bound = S_SpellData(MAKEFOURCC('F','h','p','f'), 1, 2) > 0;
    if (G_ShouldAcquireThisFrame(ent) && !(route_bound && G_ActorHasSkill(ent, "Fuwf"))) {
        float const reach = route_bound && ent->unit_state ? MAX(ent->unit_state->attack1.range, ent->unit_state->attack2.range) + ent->collision
                                                           : G_AcquisitionRange(ent);
        edict_t *enemy = G_FindNearestEnemy(ent, reach);
        if (enemy) {
            if (route_bound) ent->orders->holding_position = true;
            order_attack(ent, enemy);
            return;
        }
    }

    if (ent->goalentity != patrol_destination(ent)) {
        ent->goalentity = ent->orders->patrol_target;
        move_reset_progress(ent);
    }
    float distance = M_DistanceToGoal(ent);
    float move_distance = unit_movedistance(ent);

    if (move_should_arrive(ent, move_distance) || move_is_blocked(ent, distance, move_distance)) {
        ent->orders->patrol_to_b = !ent->orders->patrol_to_b;
        ent->orders->patrol_target = NULL;
        ent->goalentity = patrol_destination(ent);
        move_reset_progress(ent);
    } else {
        unit_changeangle(ent);
        unit_moveindirection(ent);
    }
}

static umove_t patrol_move_walk = { "walk", ai_patrol_walk, NULL, CAbilityPatrol, .travel = true };

void order_patrol_resume(edict_t *self) {
    if (S_GoldMineWorkerIsInside(self))
        return;
    self->orders->holding_position = false; /* a patrol fight's hold ends with the fight */
    self->goalentity = patrol_destination(self);
    move_reset_progress(self);
    unit_setmove(self, &patrol_move_walk);
}

void order_patrol(edict_t *self, edict_t *b) {
    if (S_GoldMineWorkerIsInside(self))
        return;
    self->orders->attackmove_waypoint = NULL;
    self->orders->patrol_a = Waypoint_add(&self->s.origin2);
    self->orders->patrol_b = b;
    self->orders->patrol_target = b;
    self->orders->patrol_point_a = (vec2_t){ self->s.origin.x, self->s.origin.y };
    self->orders->patrol_point_b = (vec2_t){ b->s.origin.x, b->s.origin.y };
    self->orders->patrol_to_b = true;
    self->orders->follow_target = NULL;
    self->orders->holding_position = false;
    order_patrol_resume(self);
}

static bool patrol_selectlocation(edict_t *clent, vec2_t const *location) {
    bool any = false;

    FOR_CONTROLLABLE_SELECTED_UNITS(clent->client, ent) {
        if ((ent->aiflags & AI_IMMOBILE) || ent->data.UnitBalance->speed <= 0) {
            continue;
        }
        vec2_t target = *location;
        CM_ClosestPathablePointForRadiusFlags(location, ent->collision, M_UnitStaticPathingFlags(ent), &target);
        order_patrol(ent, Waypoint_add(&target));
        S_UnitAbilityOrderAccepted(ent, "patrol");
        any = true;
    }
    if (any) G_SendPointConfirmation(clent, location, false);
    return any;
}

BZ_COMMAND_PROC(AbilityPatrol) {
    UI_AddCancelButton(clent);
    clent->client->menu.on_location_selected = patrol_selectlocation;
}
