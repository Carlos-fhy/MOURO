import numpy as np

from app.algorithm.base import BaseAlgorithm, SolutionResult
from app.algorithm.greedy import GreedySolver
from app.algorithm.local_search import repair_late_customers
from app.algorithm.precheck import precheck_reachability
from app.utils.objective import (
    build_schedule,
    calculate_f1,
    calculate_f2,
    calculate_f3,
    calculate_z,
    calculate_reference_z,
)


class ALNSAlgorithm(BaseAlgorithm):
    """基础版 ALNS 基线。"""

    def __init__(self, customers, depot, distance_matrix, time_matrix, params):
        super().__init__(customers, depot, distance_matrix, time_matrix, params)
        self.seed = self._default_seed
        self.removal_ratio = params.get("removal_ratio", 0.2)
        self.min_remove = params.get("min_remove", 2)
        self.max_remove = params.get("max_remove", 8)
        self.alpha_base = params.get("alpha_base", 1.0)
        self.beta_base = params.get("beta_base", 2.0)
        self.fixed_cost = params.get("fixed_cost", 200)
        self.cost_per_km = params.get("cost_per_km", 5.0)
        self.customers_dict = {c["id"]: c for c in self.customers}

    def solve(self, callback=None):
        rng = np.random.default_rng(self.seed)
        self._start_timer()
        timed_out = False

        reachable, unreachable = precheck_reachability(
            self.customers, self.depot, self.time_matrix, self.id_to_idx
        )
        unreachable_ids = [c["id"] for c in unreachable]
        working = reachable
        working_dict = {c["id"]: c for c in working}

        greedy = GreedySolver(
            working, self.depot, self.distance_matrix, self.time_matrix, self.params
        )
        greedy_result = greedy.solve()
        current_routes = [list(route) for route in greedy_result["routes"]]

        current = self._evaluate_routes(current_routes, working_dict)
        best_routes = [list(route) for route in current_routes]
        best_f1, best_f2, best_f3 = current["f1"], current["f2"], current["f3"]

        f1_min = f1_max = best_f1
        f2_min = f2_max = best_f2
        f3_min = f3_max = best_f3
        best_z = 0.0
        convergence = [(0, 0.0)]
        no_improve = 0

        for iteration in range(1, self.max_iterations + 1):
            if self._time_exceeded():
                timed_out = True
                break

            partial_routes, removed = self._destroy(current_routes, working_dict, rng)
            candidate_routes = self._repair(partial_routes, removed, working_dict)
            candidate = self._evaluate_routes(candidate_routes, working_dict)

            f1_min = min(f1_min, candidate["f1"])
            f1_max = max(f1_max, candidate["f1"])
            f2_min = min(f2_min, candidate["f2"])
            f2_max = max(f2_max, candidate["f2"])
            f3_min = min(f3_min, candidate["f3"])
            f3_max = max(f3_max, candidate["f3"])

            bounds = ((f1_min, f1_max), (f2_min, f2_max), (f3_min, f3_max))
            current_z = calculate_z(
                current["f1"], current["f2"], current["f3"],
                bounds[0], bounds[1], bounds[2], self.lambdas
            )
            candidate_z = calculate_z(
                candidate["f1"], candidate["f2"], candidate["f3"],
                bounds[0], bounds[1], bounds[2], self.lambdas
            )

            if candidate_z < current_z:
                current_routes = candidate_routes
                current = candidate
                current_z = candidate_z

            best_z_now = calculate_z(
                best_f1, best_f2, best_f3,
                bounds[0], bounds[1], bounds[2], self.lambdas
            )
            if current_z < best_z_now - self.early_stop_threshold:
                best_routes = [list(route) for route in current_routes]
                best_f1, best_f2, best_f3 = current["f1"], current["f2"], current["f3"]
                best_z = current_z
                no_improve = 0
            else:
                best_z = best_z_now
                no_improve += 1

            convergence.append((iteration, round(best_z, 6)))

            if callback:
                callback({
                    "type": "progress",
                    "iteration": iteration,
                    "best_z": round(best_z, 6),
                    "best_f1": round(best_f1, 2),
                    "best_f2": round(best_f2, 2),
                    "best_f3": round(best_f3, 2),
                    "vehicles_used": sum(1 for r in best_routes if len(r) > 2),
                })

            if no_improve >= self.patience:
                break

        if timed_out and callback:
            callback({
                "type": "timeout",
                "message": f"达到总时限 {self.max_runtime_sec:.0f}s，返回当前最优解",
                "elapsed_sec": round(self._elapsed_sec(), 2),
            })

        best_routes = repair_late_customers(
            best_routes, self.time_matrix, self.id_to_idx, working_dict
        )
        final = self._evaluate_routes(best_routes, working_dict)
        best_z = calculate_reference_z(
            final["f1"], final["f2"], final["f3"], greedy_result, self.lambdas
        )

        return SolutionResult(
            routes=best_routes,
            f1=round(final["f1"], 2),
            f2=round(final["f2"], 2),
            f3=round(final["f3"], 2),
            z=round(best_z, 6),
            vehicles_used=sum(1 for r in best_routes if len(r) > 2),
            convergence=convergence,
            schedule=final["schedule"],
            unreachable=unreachable_ids,
        )

    def _destroy(self, routes, working_dict, rng):
        flat_routes = [list(route) for route in routes]
        customer_ids = [node for route in flat_routes for node in route[1:-1]]
        if not customer_ids:
            return flat_routes, []

        remove_count = int(round(len(customer_ids) * self.removal_ratio))
        remove_count = max(self.min_remove, remove_count)
        remove_count = min(self.max_remove, remove_count, len(customer_ids))

        if rng.random() < 0.5 or len(customer_ids) <= 2:
            removed = list(rng.choice(customer_ids, size=remove_count, replace=False))
        else:
            seed_id = int(rng.choice(customer_ids))
            removed = self._related_removal(customer_ids, seed_id, remove_count, working_dict)

        removed_set = set(removed)
        new_routes = []
        for route in flat_routes:
            kept = [route[0]] + [nid for nid in route[1:-1] if nid not in removed_set] + [route[-1]]
            if len(kept) > 2:
                new_routes.append(kept)
        return new_routes, removed

    def _related_removal(self, customer_ids, seed_id, remove_count, working_dict):
        seed = working_dict[seed_id]

        def score(cid):
            node = working_dict[cid]
            i = self.id_to_idx[seed_id]
            j = self.id_to_idx[cid]
            dist = self.distance_matrix[i][j]
            tw_gap = abs(node.get("early_time", 0) - seed.get("early_time", 0))
            return dist + 0.05 * tw_gap

        ranked = sorted(customer_ids, key=score)
        return ranked[:remove_count]

    def _repair(self, routes, removed, working_dict):
        depot_id = self.depot["id"]
        repaired = [list(route) for route in routes]
        for cid in removed:
            best_choice = None
            demand = working_dict[cid].get("demand", working_dict[cid].get("demand_weight", 0))

            for route_idx, route in enumerate(repaired):
                load = sum(
                    working_dict[nid].get("demand", working_dict[nid].get("demand_weight", 0))
                    for nid in route[1:-1]
                )
                if load + demand > self.vehicle_capacity:
                    continue
                for pos in range(1, len(route)):
                    candidate = list(route)
                    candidate.insert(pos, cid)
                    if not self._route_feasible(candidate, working_dict):
                        continue
                    delta = self._route_distance(candidate) - self._route_distance(route)
                    if best_choice is None or delta < best_choice[0]:
                        best_choice = (delta, route_idx, pos)

            if best_choice is None:
                repaired.append([depot_id, cid, depot_id])
            else:
                _, route_idx, pos = best_choice
                repaired[route_idx].insert(pos, cid)
        return repaired

    def _route_feasible(self, route, working_dict):
        current_time = 0.0
        for k in range(1, len(route) - 1):
            prev_idx = self.id_to_idx[route[k - 1]]
            curr_idx = self.id_to_idx[route[k]]
            arrival = current_time + self.time_matrix[prev_idx][curr_idx]
            info = working_dict[route[k]]
            et = info.get("early_time", 0)
            lt = info.get("late_time", float("inf"))
            st = info.get("service_time", 0)
            level = info.get("emergency_level", "normal")
            if arrival > lt:
                return False
            if arrival < et and level == "medical":
                current_time = et + st
            else:
                current_time = max(arrival, et) + st if level == "medical" else arrival + st
        return True

    def _route_distance(self, route):
        total = 0.0
        for k in range(len(route) - 1):
            i = self.id_to_idx[route[k]]
            j = self.id_to_idx[route[k + 1]]
            total += self.distance_matrix[i][j]
        return total

    def _evaluate_routes(self, routes, working_dict):
        schedule = build_schedule(
            routes, working_dict, self.time_matrix,
            self.id_to_idx, self.alpha_base, self.beta_base
        )
        f1 = calculate_f1(
            routes, self.distance_matrix, self.id_to_idx,
            self.fixed_cost, self.cost_per_km
        )
        f2 = calculate_f2(schedule, working_dict)
        f3 = calculate_f3(schedule, working_dict)
        return {"routes": routes, "f1": f1, "f2": f2, "f3": f3, "schedule": schedule}
