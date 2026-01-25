-- ============================================================================
-- SETTLEMENTS DATABASE SCHEMA
-- ============================================================================
-- Version: 1.0
-- Date: 2025-10-14
-- Source: settlement_ground_truth.json v2.37
-- Total Settlements: 476 (180 gondola, 262 isolated, 34 boundary/edge)
-- ============================================================================

-- Drop existing tables if they exist (for clean rebuild)
DROP TABLE IF EXISTS cable_car_settlements;
DROP TABLE IF EXISTS stitching_anchors;
DROP TABLE IF EXISTS cable_car_lines;
DROP TABLE IF EXISTS settlements;
DROP TABLE IF EXISTS gondola_systems;

-- ============================================================================
-- GONDOLA SYSTEMS TABLE
-- ============================================================================
-- Gondola/cable car systems (30 total)
-- Each system is a connected line of stations spanning low-to-high altitude
-- ============================================================================

CREATE TABLE gondola_systems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- System identification
    system_name TEXT NOT NULL UNIQUE,      -- "G1", "G2", "G3"...
    system_number INTEGER NOT NULL UNIQUE, -- 1, 2, 3...

    -- Metadata
    primary_tile_id TEXT NOT NULL,         -- Tile where system originates
    line_type TEXT NOT NULL,               -- "horizontal" | "vertical"
    station_count INTEGER NOT NULL,        -- Total stations (origin + pylons + terminus)

    -- Origin/Terminus detection
    origin_tile_id TEXT NOT NULL,          -- Tile containing origin station
    origin_x INTEGER NOT NULL,             -- Origin pixel X
    origin_y INTEGER NOT NULL,             -- Origin pixel Y
    origin_brightness REAL,                -- Terrain brightness at origin (brighter=lower)
    origin_terrain_type TEXT,              -- GREEN | BROWN | DARK | etc.

    terminus_tile_id TEXT NOT NULL,        -- Tile containing terminus station
    terminus_x INTEGER NOT NULL,           -- Terminus pixel X
    terminus_y INTEGER NOT NULL,           -- Terminus pixel Y
    terminus_brightness REAL,              -- Terrain brightness at terminus (darker=higher)
    terminus_terrain_type TEXT,            -- GREEN | BROWN | DARK | etc.

    brightness_delta REAL,                 -- abs(origin - terminus) brightness

    -- Spatial info
    spans_multiple_tiles BOOLEAN DEFAULT 0,
    tile_list TEXT,                        -- JSON array: ["D7", "E7"]

    -- Cable car line axis
    axis_coordinate INTEGER,               -- X for vertical lines, Y for horizontal

    -- Notes
    notes TEXT,
    created_date TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_gondola_system_name ON gondola_systems(system_name);
CREATE INDEX idx_gondola_primary_tile ON gondola_systems(primary_tile_id);

-- ============================================================================
-- SETTLEMENTS TABLE
-- ============================================================================
-- All 476 detected settlements with precise coordinates and metadata
-- Includes both gondola stations (IN_LINE) and isolated settlements
-- ============================================================================

CREATE TABLE settlements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- ========================================================================
    -- NAMING SYSTEM
    -- ========================================================================
    system_name TEXT NOT NULL UNIQUE,     -- "G1-ORIGIN", "B10-S01", etc.
    display_name TEXT,                     -- User-provided name (nullable)
    name_aliases TEXT,                     -- JSON array of alternative names

    -- ========================================================================
    -- GONDOLA SYSTEM REFERENCE (for IN_LINE settlements only)
    -- ========================================================================
    gondola_system_id INTEGER,             -- FK to gondola_systems, NULL for isolated
    gondola_role TEXT,                     -- "ORIGIN" | "PYLON" | "TERMINUS" | NULL
    gondola_sequence INTEGER,              -- 0=origin, 1-N=pylons, N+1=terminus, NULL for isolated

    -- ========================================================================
    -- TILE IDENTIFICATION
    -- ========================================================================
    tile_id TEXT NOT NULL,                 -- "B10", "C12", etc.
    tile_row INTEGER NOT NULL,             -- 0-15 (A=0, B=1, P=15)
    tile_col INTEGER NOT NULL,             -- 0-15 (1=0, 2=1, 16=15)

    -- ========================================================================
    -- COORDINATES
    -- ========================================================================
    -- Pixel coordinates (within tile)
    pixel_x INTEGER NOT NULL,              -- 0-1599 within tile
    pixel_y INTEGER NOT NULL,              -- 0-1599 within tile

    -- World coordinates (calculated)
    world_x REAL NOT NULL,                 -- meters in world space (644km map)
    world_z REAL NOT NULL,                 -- meters in world space
    elevation_m REAL,                      -- elevation in meters (from heightmap, nullable)

    -- ========================================================================
    -- DETECTION METADATA
    -- ========================================================================
    validated BOOLEAN NOT NULL DEFAULT 1,
    spatial_type TEXT NOT NULL,            -- ISOLATED | IN_LINE | BOUNDARY_VALIDATED | BOUNDARY | EDGE
    enemy_occupied BOOLEAN NOT NULL DEFAULT 0,
    detection_confidence TEXT,             -- HIGH | MEDIUM | LOW (from Rule 15 detection)

    -- Terrain sampling (from terrain_sampler.py)
    terrain_brightness REAL,               -- Average brightness around settlement
    terrain_rgb TEXT,                      -- JSON: {"r": 185, "g": 53, "b": 1}
    terrain_type TEXT,                     -- GREEN | BROWN | DARK | SNOW | WATER | MIXED

    -- ========================================================================
    -- NOTES & METADATA
    -- ========================================================================
    notes TEXT,
    detection_version TEXT DEFAULT '2.37', -- Ground truth version
    created_date TEXT DEFAULT CURRENT_TIMESTAMP,

    -- ========================================================================
    -- FOREIGN KEY CONSTRAINTS
    -- ========================================================================
    FOREIGN KEY (gondola_system_id) REFERENCES gondola_systems(id),

    -- ========================================================================
    -- UNIQUE CONSTRAINTS
    -- ========================================================================
    UNIQUE(tile_id, pixel_x, pixel_y)      -- No duplicate settlements at same location
);

-- Indices for fast queries
CREATE INDEX idx_settlements_system_name ON settlements(system_name);
CREATE INDEX idx_settlements_tile ON settlements(tile_id);
CREATE INDEX idx_settlements_coords ON settlements(tile_id, pixel_x, pixel_y);
CREATE INDEX idx_settlements_world ON settlements(world_x, world_z);
CREATE INDEX idx_settlements_spatial ON settlements(spatial_type);
CREATE INDEX idx_settlements_gondola ON settlements(gondola_system_id);
CREATE INDEX idx_settlements_enemy ON settlements(enemy_occupied);

-- ============================================================================
-- CABLE CAR LINES TABLE
-- ============================================================================
-- Individual cable car line segments within tiles
-- May be part of larger cross-tile gondola systems
-- ============================================================================

CREATE TABLE cable_car_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Line identification
    tile_id TEXT NOT NULL,
    line_type TEXT NOT NULL,               -- "horizontal" | "vertical"
    axis_coordinate INTEGER NOT NULL,      -- X for vertical, Y for horizontal
    settlement_count INTEGER NOT NULL,     -- Number of settlements in this line segment

    -- Gondola system reference
    gondola_system_id INTEGER,             -- FK to gondola_systems, NULL if not analyzed

    -- Notes
    notes TEXT,

    FOREIGN KEY (gondola_system_id) REFERENCES gondola_systems(id)
);

CREATE INDEX idx_cable_tile ON cable_car_lines(tile_id);
CREATE INDEX idx_cable_gondola ON cable_car_lines(gondola_system_id);

-- ============================================================================
-- CABLE CAR SETTLEMENTS JUNCTION TABLE
-- ============================================================================
-- Maps which settlements belong to which cable car lines
-- ============================================================================

CREATE TABLE cable_car_settlements (
    cable_car_line_id INTEGER NOT NULL,
    settlement_id INTEGER NOT NULL,
    sequence_number INTEGER,               -- Order along the line (0-based)

    PRIMARY KEY (cable_car_line_id, settlement_id),
    FOREIGN KEY (cable_car_line_id) REFERENCES cable_car_lines(id),
    FOREIGN KEY (settlement_id) REFERENCES settlements(id)
);

CREATE INDEX idx_ccs_line ON cable_car_settlements(cable_car_line_id);
CREATE INDEX idx_ccs_settlement ON cable_car_settlements(settlement_id);

-- ============================================================================
-- STITCHING ANCHORS TABLE
-- ============================================================================
-- Boundary settlements used for tile stitching alignment (14 total)
-- Critical for seamless terrain generation
-- ============================================================================

CREATE TABLE stitching_anchors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Anchor identification
    anchor_id INTEGER UNIQUE NOT NULL,     -- 1-14 from ground truth
    anchor_type TEXT NOT NULL,             -- "settlement_pair" | "orphan_settlement" | "cable_car_line"

    -- Tiles involved
    tile1_id TEXT NOT NULL,
    tile2_id TEXT,                         -- Nullable for orphans
    edge TEXT NOT NULL,                    -- "G8_BOTTOM-H8_TOP", etc.

    -- Settlement references
    settlement1_id INTEGER,                -- FK to settlements
    settlement2_id INTEGER,                -- FK to settlements

    -- Cable car reference
    cable_car_line_id INTEGER,             -- FK to cable_car_lines
    gondola_system_id INTEGER,             -- FK to gondola_systems

    -- Alignment data
    distance_pixels INTEGER,               -- Pixel distance between paired settlements
    settlement_count INTEGER,              -- For cable car line anchors

    -- Notes
    notes TEXT,

    FOREIGN KEY (settlement1_id) REFERENCES settlements(id),
    FOREIGN KEY (settlement2_id) REFERENCES settlements(id),
    FOREIGN KEY (cable_car_line_id) REFERENCES cable_car_lines(id),
    FOREIGN KEY (gondola_system_id) REFERENCES gondola_systems(id)
);

CREATE INDEX idx_anchor_tiles ON stitching_anchors(tile1_id, tile2_id);
CREATE INDEX idx_anchor_type ON stitching_anchors(anchor_type);

-- ============================================================================
-- SUMMARY STATISTICS VIEW
-- ============================================================================

CREATE VIEW settlement_stats AS
SELECT
    COUNT(*) as total_settlements,
    SUM(CASE WHEN spatial_type = 'ISOLATED' THEN 1 ELSE 0 END) as isolated_count,
    SUM(CASE WHEN spatial_type = 'IN_LINE' THEN 1 ELSE 0 END) as gondola_count,
    SUM(CASE WHEN spatial_type = 'BOUNDARY_VALIDATED' THEN 1 ELSE 0 END) as boundary_count,
    SUM(CASE WHEN enemy_occupied = 1 THEN 1 ELSE 0 END) as enemy_occupied_count,
    (SELECT COUNT(*) FROM gondola_systems) as gondola_systems_count
FROM settlements;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
