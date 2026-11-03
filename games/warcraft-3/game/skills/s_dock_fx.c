/* Dry-dock presentation for the dock-repair logic in s_veterancy.c (which keeps weak no-op
 * fallbacks): the caisson gate and the wake of a newly built ship pushed out to sea.
 * tools/frontline/drydock.py: 'Stand Alternate' floats the caisson out and holds it open;
 * Stand / Stand Work keep it shut. tools/frontline/naval_fx.py builds launch_wake.mdx. */
#include "s_skills.h"
#define BZ_DOCK_FX 1  /* replaces the weak fallbacks in s_veterancy.c */

#define DOCK_GATE_TAG "alternate"
#define LAUNCH_WAKE_LENGTH 200.0f // world units; hull length launch_wake.mdx is drawn for

void S_DockGate(edict_t *dock, bool open) {
    if (!dock || !dock->inuse) return;
    G_AddUnitAnimationProperties(dock, DOCK_GATE_TAG, open);
}

/* Stern churn, a widening foam V and bow spray at the ship, scaled to its hull and turned
 * to the heading it leaves on. Purely visual: the push itself is the caller's move order. */
void S_ShipLaunchFx(edict_t *ship, edict_t *dock) {
    if (!ship || !ship->inuse) return;
    edict_t wake = {0};
    wake.s = ship->s;
    wake.s.origin.z = 0;
    wake.s.origin2 = (vec2_t){ ship->s.origin.x, ship->s.origin.y };
    wake.s.scale = MAX(0.5f, MIN(1.8f, ship->collision * 4.0f / LAUNCH_WAKE_LENGTH));
    wake.s.model = G_RegisterModel("Emberfield/Models/launch_wake.mdx");
    (void)dock;
    G_SpawnProjectileImpact(&wake);
}
