param allowCollisions = True

class GenObject(Object):
    is_actor : False
    allowCollisions : True

class Actor(GenObject):
    id : int
    length : 1
    is_vessel : False
    is_actor : True

class Obstacle(Actor):
    area_radius : float

class Vessel(Actor):
    is_vessel : True
    is_os : False
    max_speed : GlobalConfig.MAX_SPEED_IN_MS

class OwnShip(Vessel):
    is_os : True


def create_scenario(os_id, ts_ids, obst_ids, length_map, radius_map, possible_distances_map, min_distance_map, vis_distance_map, bearing_map):
    os_radius = radius_map[os_id]
    os_length = length_map[os_id]
    ego = new OwnShip with id os_id, with length os_length, at (GlobalConfig.MAX_COORD/2, GlobalConfig.MAX_COORD/2), with velocity (0, Range(GlobalConfig.MIN_SPEED_IN_MS, GlobalConfig.MAX_SPEED_IN_MS)), facing toward (GlobalConfig.MAX_COORD/2, GlobalConfig.MAX_COORD)

    def add_ts(ts_id):
        ts_length = length_map[ts_id]
        ts_radius = radius_map[ts_id]
        heading_ego_to_ts, bearing_angle_ego_to_ts, heading_ts_to_ego, bearing_angle_ts_to_ego = bearing_map.get((os_id, ts_id), (0, 2*np.pi, 0, 2*np.pi))
        
        visibility_dist = vis_distance_map.get((os_id, ts_id), None)
        
        if visibility_dist is not None:
            distance_region = CircularRegion(ego.position, visibility_dist + GlobalConfig.DIST_DRIFT - GlobalConfig.EPSILON).difference(CircularRegion(ego.position, visibility_dist - GlobalConfig.DIST_DRIFT + GlobalConfig.EPSILON))
            min_distance = visibility_dist
        else:
            dist1 = possible_distances_map[(os_id, ts_id)][0]
            dist2 = possible_distances_map[(os_id, ts_id)][1]
            dist3 = possible_distances_map[(os_id, ts_id)][2]
            dist4 = possible_distances_map[(os_id, ts_id)][3]

            region_1 = CircularRegion(ego.position, dist1 + GlobalConfig.DIST_DRIFT - GlobalConfig.EPSILON).difference(CircularRegion(ego.position, dist1 - GlobalConfig.DIST_DRIFT + GlobalConfig.EPSILON))
            region_2 = CircularRegion(ego.position, dist2 + GlobalConfig.DIST_DRIFT - GlobalConfig.EPSILON).difference(CircularRegion(ego.position, dist2 - GlobalConfig.DIST_DRIFT + GlobalConfig.EPSILON))
            region_3 = CircularRegion(ego.position, dist3 + GlobalConfig.DIST_DRIFT - GlobalConfig.EPSILON).difference(CircularRegion(ego.position, dist3 - GlobalConfig.DIST_DRIFT + GlobalConfig.EPSILON))
            region_4 = CircularRegion(ego.position, dist4 + GlobalConfig.DIST_DRIFT - GlobalConfig.EPSILON).difference(CircularRegion(ego.position, dist4 - GlobalConfig.DIST_DRIFT + GlobalConfig.EPSILON))

            distance_region = region_1.union(region_2).union(region_3).union(region_4)
            min_distance = min_distance_map[(os_id, ts_id)]


        bearing_region_ego_to_ts = SectorRegion(ego.position, GlobalConfig.MAX_DISTANCE*3, heading_ego_to_ts + ego.heading, bearing_angle_ego_to_ts - GlobalConfig.EPSILON)
        
        ts_point_region = distance_region.intersect(bearing_region_ego_to_ts)
        ts_point = new Point in ts_point_region

        speed_region = CircularRegion(ts_point.position, GlobalConfig.MAX_SPEED_IN_MS - GlobalConfig.EPSILON).difference(CircularRegion(ts_point.position, GlobalConfig.MIN_SPEED_IN_MS + GlobalConfig.EPSILON))
        p21 = new GenObject facing toward ego.position - ts_point.position
        bearing_region_ts_to_ego = SectorRegion(ts_point.position, GlobalConfig.MAX_DISTANCE*3, heading_ts_to_ego + p21.heading, bearing_angle_ts_to_ego - GlobalConfig.EPSILON)
        
        sin_half_cone_theta = np.clip(max(ts_radius, os_radius) / min_distance, -1, 1)
        angle_half_cone = abs(np.arcsin(sin_half_cone_theta))
        voc_region = SectorRegion(ts_point.position + ego.velocity, GlobalConfig.MAX_DISTANCE*3, p21.heading, 2 * angle_half_cone)

        ts_velocity_region = speed_region.intersect(voc_region).intersect(bearing_region_ts_to_ego)

        velocity_point = new Point in ts_velocity_region
        ts = new Vessel with id ts_id, at ts_point.position, with velocity velocity_point.position-ts_point.position, with length ts_length
        return ts


    def add_obst(obst_id):
        visibility_dist = vis_distance_map[(os_id, obst_id)]
        obst_radius = radius_map[obst_id]
        heading_ego_to_obst, bearing_angle_ego_to_obst, heading_obst_to_ego, bearing_angle_obst_to_ego = bearing_map.get((os_id, obst_id), (0, 2*np.pi, 0, 2*np.pi))
        
        distance_region = CircularRegion(ego.position, visibility_dist + GlobalConfig.DIST_DRIFT - GlobalConfig.EPSILON).difference(CircularRegion(ego.position, visibility_dist - GlobalConfig.DIST_DRIFT + GlobalConfig.EPSILON))
        distance = visibility_dist

        bearing_region_ego_to_obst = SectorRegion(ego.position, GlobalConfig.MAX_DISTANCE*3, heading_ego_to_obst + ego.heading, bearing_angle_ego_to_obst - GlobalConfig.EPSILON)
        
        sin_half_cone_theta = np.clip(max(obst_radius, os_radius) / distance, -1, 1)
        angle_half_cone = abs(np.arcsin(sin_half_cone_theta))
        voc_region = SectorRegion(ego.position, CONFIG.MAX_DISTANCE*3, ego.heading, 2 * angle_half_cone)
        
        obst_point_region = distance_region.intersect(bearing_region_ego_to_obst).intersect(voc_region)
        obst_point = new Point in obst_point_region

        obst = new Obstacle with id obst_id, at obst_point.position, with area_radius obst_radius
        return obst

    return [add_ts(ts_id) for ts_id in ts_ids], [add_obst(obst_id) for obst_id in obst_ids]