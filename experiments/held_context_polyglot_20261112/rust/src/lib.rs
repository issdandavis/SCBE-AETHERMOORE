//! Dependency-free reference codec and bounded cache for HeldContextPacket v1.

use std::collections::BTreeMap;
use std::error::Error;
use std::fmt::{Display, Formatter};

pub const HEADER_LEN: usize = 64;
pub const LANE_HEADER_LEN: usize = 96;
pub const Q_SCALE: i32 = 1_000_000;
pub const NO_EXPIRY: u64 = u64::MAX;
pub const MAX_BODY_LEN: usize = 16 * 1024 * 1024;
pub const MAX_LANES: usize = 4096;
pub const MAX_ROUTE_DIM: usize = 256;
pub const MAX_TOKEN_COUNT: usize = 1_048_576;
pub const MAX_PAYLOAD_LEN: usize = 8 * 1024 * 1024;
pub const MAX_SNAPSHOT_LEN: usize = 64 * 1024 * 1024;

const MAGIC: &[u8; 4] = b"HCTX";
const VERSION: u8 = 1;
const SNAPSHOT_MAGIC: &[u8; 4] = b"HCCH";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PacketError(pub String);

impl Display for PacketError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

impl Error for PacketError {}

fn err(message: impl Into<String>) -> PacketError {
    PacketError(message.into())
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum LaneKind {
    Root = 0,
    Linguistic = 1,
    Route = 2,
    Tool = 3,
    Speech = 4,
    Geometry = 5,
    Receipt = 6,
    Custom = 7,
}

impl TryFrom<u8> for LaneKind {
    type Error = PacketError;

    fn try_from(value: u8) -> Result<Self, Self::Error> {
        match value {
            0 => Ok(Self::Root),
            1 => Ok(Self::Linguistic),
            2 => Ok(Self::Route),
            3 => Ok(Self::Tool),
            4 => Ok(Self::Speech),
            5 => Ok(Self::Geometry),
            6 => Ok(Self::Receipt),
            7 => Ok(Self::Custom),
            _ => Err(err("unknown lane kind")),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum EvidenceState {
    Present = 0,
    Missing = 1,
    Neutral = 2,
    Silence = 3,
    Abstain = 4,
}

impl TryFrom<u8> for EvidenceState {
    type Error = PacketError;

    fn try_from(value: u8) -> Result<Self, Self::Error> {
        match value {
            0 => Ok(Self::Present),
            1 => Ok(Self::Missing),
            2 => Ok(Self::Neutral),
            3 => Ok(Self::Silence),
            4 => Ok(Self::Abstain),
            _ => Err(err("unknown evidence state")),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum LaneRole {
    Independent = 0,
    Derived = 1,
    Control = 2,
    Observed = 3,
    Computed = 4,
    Provenance = 5,
}

impl TryFrom<u8> for LaneRole {
    type Error = PacketError;

    fn try_from(value: u8) -> Result<Self, Self::Error> {
        match value {
            0 => Ok(Self::Independent),
            1 => Ok(Self::Derived),
            2 => Ok(Self::Control),
            3 => Ok(Self::Observed),
            4 => Ok(Self::Computed),
            5 => Ok(Self::Provenance),
            _ => Err(err("unknown lane role")),
        }
    }
}

pub const FLAG_PINNED: u8 = 1 << 0;
pub const FLAG_COMPRESSIBLE: u8 = 1 << 1;
pub const FLAG_EXACT_BYTES: u8 = 1 << 2;
const KNOWN_FLAGS: u8 = FLAG_PINNED | FLAG_COMPRESSIBLE | FLAG_EXACT_BYTES;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HeldContextLane {
    pub lane_id: u16,
    pub kind: LaneKind,
    pub evidence: EvidenceState,
    pub role: LaneRole,
    pub flags: u8,
    pub route_q1e6: Vec<i32>,
    pub token_ids: Vec<u32>,
    pub payload: Vec<u8>,
    pub expiry_sequence: u64,
    pub canonical_value_id: [u8; 32],
    pub source_hash: [u8; 32],
}

impl HeldContextLane {
    pub fn validate(&self) -> Result<(), PacketError> {
        if self.flags & !KNOWN_FLAGS != 0 {
            return Err(err("unknown lane flag bit"));
        }
        if self.route_q1e6.len() > MAX_ROUTE_DIM {
            return Err(err("route dimension exceeds v1 limit"));
        }
        if self.token_ids.len() > MAX_TOKEN_COUNT {
            return Err(err("token count exceeds v1 limit"));
        }
        if self.payload.len() > MAX_PAYLOAD_LEN {
            return Err(err("payload exceeds v1 limit"));
        }
        Ok(())
    }

    fn encode(&self) -> Result<Vec<u8>, PacketError> {
        self.validate()?;
        let variable_len = self
            .route_q1e6
            .len()
            .checked_mul(4)
            .and_then(|n| n.checked_add(self.token_ids.len() * 4))
            .and_then(|n| n.checked_add(self.payload.len()))
            .ok_or_else(|| err("lane size overflow"))?;
        let mut variable = Vec::with_capacity(variable_len);
        for value in &self.route_q1e6 {
            variable.extend_from_slice(&value.to_le_bytes());
        }
        for value in &self.token_ids {
            variable.extend_from_slice(&value.to_le_bytes());
        }
        variable.extend_from_slice(&self.payload);

        let mut header = vec![0u8; LANE_HEADER_LEN];
        put_u16(&mut header, 0, self.lane_id);
        header[2] = self.kind as u8;
        header[3] = self.evidence as u8;
        header[4] = self.role as u8;
        header[5] = self.flags;
        put_u16(&mut header, 6, self.route_q1e6.len() as u16);
        put_u32(&mut header, 8, self.token_ids.len() as u32);
        put_u32(&mut header, 12, self.payload.len() as u32);
        put_u64(&mut header, 16, self.expiry_sequence);
        header[24..56].copy_from_slice(&self.canonical_value_id);
        header[56..88].copy_from_slice(&self.source_hash);
        let mut checksum_input = Vec::with_capacity(88 + variable.len());
        checksum_input.extend_from_slice(&header[..88]);
        checksum_input.extend_from_slice(&variable);
        put_u32(&mut header, 88, crc32(&checksum_input));

        header.extend_from_slice(&variable);
        Ok(header)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HeldContextPacket {
    pub packet_id: [u8; 16],
    pub generation: u32,
    pub sequence_cutoff: u64,
    pub token_budget: u32,
    pub breath_q1e6: i32,
    pub radius_q1e6: i32,
    pub flags: u8,
    pub lanes: Vec<HeldContextLane>,
}

impl HeldContextPacket {
    pub fn validate(&self) -> Result<(), PacketError> {
        if self.radius_q1e6 < 0 || self.radius_q1e6 >= Q_SCALE {
            return Err(err("radius_q1e6 must remain inside the unit ball"));
        }
        if self.lanes.len() > MAX_LANES {
            return Err(err("lane count exceeds v1 limit"));
        }
        let mut previous = None;
        for lane in &self.lanes {
            lane.validate()?;
            if let Some(value) = previous {
                if lane.lane_id <= value {
                    return Err(err("lanes must have unique ascending lane IDs"));
                }
            }
            if lane.expiry_sequence != NO_EXPIRY && lane.expiry_sequence < self.sequence_cutoff {
                return Err(err("packet contains a lane expired before sequence cutoff"));
            }
            previous = Some(lane.lane_id);
        }
        Ok(())
    }

    pub fn encode(&self) -> Result<Vec<u8>, PacketError> {
        self.validate()?;
        let mut body = Vec::new();
        for lane in &self.lanes {
            body.extend_from_slice(&lane.encode()?);
        }
        if body.len() > MAX_BODY_LEN {
            return Err(err("packet body exceeds v1 limit"));
        }
        let mut header = vec![0u8; HEADER_LEN];
        header[0..4].copy_from_slice(MAGIC);
        header[4] = VERSION;
        header[5] = self.flags;
        put_u16(&mut header, 6, HEADER_LEN as u16);
        put_u32(&mut header, 8, body.len() as u32);
        put_u16(&mut header, 12, self.lanes.len() as u16);
        put_u64(&mut header, 16, self.sequence_cutoff);
        put_u32(&mut header, 24, self.token_budget);
        put_i32(&mut header, 28, self.breath_q1e6);
        put_i32(&mut header, 32, self.radius_q1e6);
        header[36..52].copy_from_slice(&self.packet_id);
        put_u32(&mut header, 52, self.generation);
        put_u32(&mut header, 56, crc32(&body));
        let header_crc = crc32(&header[..60]);
        put_u32(&mut header, 60, header_crc);
        header.extend_from_slice(&body);
        Ok(header)
    }

    pub fn decode(raw: &[u8]) -> Result<Self, PacketError> {
        if raw.len() < HEADER_LEN {
            return Err(err("truncated packet header"));
        }
        if &raw[0..4] != MAGIC || raw[4] != VERSION || read_u16(raw, 6)? as usize != HEADER_LEN {
            return Err(err("unsupported packet magic, version, or header length"));
        }
        if read_u16(raw, 14)? != 0 {
            return Err(err("packet reserved field must be zero"));
        }
        let body_len = read_u32(raw, 8)? as usize;
        let lane_count = read_u16(raw, 12)? as usize;
        if body_len > MAX_BODY_LEN || lane_count > MAX_LANES {
            return Err(err("declared packet dimensions exceed v1 limits"));
        }
        if raw.len() != HEADER_LEN + body_len {
            return Err(err("packet length does not match body length"));
        }
        if crc32(&raw[..60]) != read_u32(raw, 60)? {
            return Err(err("header CRC mismatch"));
        }
        let body = &raw[HEADER_LEN..];
        if crc32(body) != read_u32(raw, 56)? {
            return Err(err("body CRC mismatch"));
        }

        let mut lanes = Vec::with_capacity(lane_count);
        let mut offset = 0usize;
        for _ in 0..lane_count {
            if body_len.saturating_sub(offset) < LANE_HEADER_LEN {
                return Err(err("truncated lane header"));
            }
            let header = &body[offset..offset + LANE_HEADER_LEN];
            if read_u32(header, 92)? != 0 {
                return Err(err("lane reserved field must be zero"));
            }
            let route_dim = read_u16(header, 6)? as usize;
            let token_count = read_u32(header, 8)? as usize;
            let payload_len = read_u32(header, 12)? as usize;
            if route_dim > MAX_ROUTE_DIM
                || token_count > MAX_TOKEN_COUNT
                || payload_len > MAX_PAYLOAD_LEN
            {
                return Err(err("declared lane dimensions exceed v1 limits"));
            }
            let variable_len = route_dim
                .checked_mul(4)
                .and_then(|n| n.checked_add(token_count.checked_mul(4)?))
                .and_then(|n| n.checked_add(payload_len))
                .ok_or_else(|| err("lane size overflow"))?;
            let lane_end = offset
                .checked_add(LANE_HEADER_LEN)
                .and_then(|n| n.checked_add(variable_len))
                .ok_or_else(|| err("lane offset overflow"))?;
            if lane_end > body_len {
                return Err(err("truncated lane variable data"));
            }
            let variable = &body[offset + LANE_HEADER_LEN..lane_end];
            let mut checksum_input = Vec::with_capacity(88 + variable_len);
            checksum_input.extend_from_slice(&header[..88]);
            checksum_input.extend_from_slice(variable);
            if crc32(&checksum_input) != read_u32(header, 88)? {
                return Err(err("lane CRC mismatch"));
            }
            let mut route_q1e6 = Vec::with_capacity(route_dim);
            for index in 0..route_dim {
                route_q1e6.push(read_i32(variable, index * 4)?);
            }
            let token_offset = route_dim * 4;
            let mut token_ids = Vec::with_capacity(token_count);
            for index in 0..token_count {
                token_ids.push(read_u32(variable, token_offset + index * 4)?);
            }
            let payload_offset = token_offset + token_count * 4;
            let mut canonical_value_id = [0u8; 32];
            canonical_value_id.copy_from_slice(&header[24..56]);
            let mut source_hash = [0u8; 32];
            source_hash.copy_from_slice(&header[56..88]);
            lanes.push(HeldContextLane {
                lane_id: read_u16(header, 0)?,
                kind: LaneKind::try_from(header[2])?,
                evidence: EvidenceState::try_from(header[3])?,
                role: LaneRole::try_from(header[4])?,
                flags: header[5],
                route_q1e6,
                token_ids,
                payload: variable[payload_offset..].to_vec(),
                expiry_sequence: read_u64(header, 16)?,
                canonical_value_id,
                source_hash,
            });
            offset = lane_end;
        }
        if offset != body_len {
            return Err(err("unclaimed bytes remain after final lane"));
        }
        let mut packet_id = [0u8; 16];
        packet_id.copy_from_slice(&raw[36..52]);
        let packet = Self {
            packet_id,
            generation: read_u32(raw, 52)?,
            sequence_cutoff: read_u64(raw, 16)?,
            token_budget: read_u32(raw, 24)?,
            breath_q1e6: read_i32(raw, 28)?,
            radius_q1e6: read_i32(raw, 32)?,
            flags: raw[5],
            lanes,
        };
        packet.validate()?;
        Ok(packet)
    }

    pub fn is_pinned(&self) -> bool {
        self.lanes.iter().any(|lane| lane.flags & FLAG_PINNED != 0)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct CacheEntry {
    raw: Vec<u8>,
    generation: u32,
    last_access: u64,
    pinned: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HeldContextCache {
    capacity_bytes: usize,
    used_bytes: usize,
    clock: u64,
    entries: BTreeMap<[u8; 16], CacheEntry>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InsertOutcome {
    Inserted,
    Replaced,
    Unchanged,
}

impl HeldContextCache {
    pub fn new(capacity_bytes: usize) -> Result<Self, PacketError> {
        if capacity_bytes == 0 || capacity_bytes > MAX_SNAPSHOT_LEN {
            return Err(err(
                "cache capacity must be between 1 byte and the snapshot limit",
            ));
        }
        Ok(Self {
            capacity_bytes,
            used_bytes: 0,
            clock: 0,
            entries: BTreeMap::new(),
        })
    }

    pub fn capacity_bytes(&self) -> usize {
        self.capacity_bytes
    }

    pub fn used_bytes(&self) -> usize {
        self.used_bytes
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    pub fn contains(&self, packet_id: &[u8; 16]) -> bool {
        self.entries.contains_key(packet_id)
    }

    pub fn get(&mut self, packet_id: &[u8; 16]) -> Option<Vec<u8>> {
        let entry = self.entries.get_mut(packet_id)?;
        self.clock = self.clock.saturating_add(1);
        entry.last_access = self.clock;
        Some(entry.raw.clone())
    }

    pub fn insert(&mut self, raw: &[u8]) -> Result<InsertOutcome, PacketError> {
        let packet = HeldContextPacket::decode(raw)?;
        if raw.len() > self.capacity_bytes {
            return Err(err("packet exceeds cache capacity"));
        }
        if let Some(existing) = self.entries.get(&packet.packet_id) {
            if packet.generation < existing.generation {
                return Err(err("stale packet generation"));
            }
            if packet.generation == existing.generation {
                if raw == existing.raw {
                    self.clock = self.clock.saturating_add(1);
                    self.entries
                        .get_mut(&packet.packet_id)
                        .expect("entry exists")
                        .last_access = self.clock;
                    return Ok(InsertOutcome::Unchanged);
                }
                return Err(err("generation collision with different bytes"));
            }
        }

        let replaced = self.entries.contains_key(&packet.packet_id);
        let mut planned = self.entries.clone();
        planned.remove(&packet.packet_id);
        let next_clock = self.clock.saturating_add(1);
        planned.insert(
            packet.packet_id,
            CacheEntry {
                raw: raw.to_vec(),
                generation: packet.generation,
                last_access: next_clock,
                pinned: packet.is_pinned(),
            },
        );
        while total_bytes(&planned) > self.capacity_bytes {
            let candidate = planned
                .iter()
                .filter(|(id, entry)| **id != packet.packet_id && !entry.pinned)
                .min_by_key(|(id, entry)| (entry.last_access, **id))
                .map(|(id, _)| *id);
            match candidate {
                Some(id) => {
                    planned.remove(&id);
                }
                None => return Err(err("cache capacity is held by pinned packets")),
            }
        }
        self.entries = planned;
        self.used_bytes = total_bytes(&self.entries);
        self.clock = next_clock;
        Ok(if replaced {
            InsertOutcome::Replaced
        } else {
            InsertOutcome::Inserted
        })
    }

    pub fn snapshot(&self) -> Result<Vec<u8>, PacketError> {
        let mut body = Vec::new();
        for (packet_id, entry) in &self.entries {
            body.extend_from_slice(packet_id);
            body.extend_from_slice(&entry.generation.to_le_bytes());
            body.extend_from_slice(&entry.last_access.to_le_bytes());
            body.push(u8::from(entry.pinned));
            body.extend_from_slice(&[0u8; 3]);
            body.extend_from_slice(&(entry.raw.len() as u32).to_le_bytes());
            body.extend_from_slice(&entry.raw);
        }
        if body.len() + 36 > MAX_SNAPSHOT_LEN {
            return Err(err("cache snapshot exceeds v1 limit"));
        }
        let mut output = Vec::with_capacity(36 + body.len());
        output.extend_from_slice(SNAPSHOT_MAGIC);
        output.push(1);
        output.extend_from_slice(&[0u8; 3]);
        output.extend_from_slice(&(self.capacity_bytes as u64).to_le_bytes());
        output.extend_from_slice(&self.clock.to_le_bytes());
        output.extend_from_slice(&(self.entries.len() as u32).to_le_bytes());
        output.extend_from_slice(&(body.len() as u32).to_le_bytes());
        output.extend_from_slice(&crc32(&body).to_le_bytes());
        output.extend_from_slice(&body);
        Ok(output)
    }

    pub fn restore(raw: &[u8], maximum_capacity: usize) -> Result<Self, PacketError> {
        if raw.len() < 36 || raw.len() > MAX_SNAPSHOT_LEN {
            return Err(err("invalid cache snapshot length"));
        }
        if &raw[..4] != SNAPSHOT_MAGIC || raw[4] != 1 || raw[5..8] != [0, 0, 0] {
            return Err(err("unsupported cache snapshot header"));
        }
        let capacity_u64 = read_u64(raw, 8)?;
        if capacity_u64 > usize::MAX as u64 {
            return Err(err("snapshot capacity does not fit this platform"));
        }
        let capacity = capacity_u64 as usize;
        if capacity == 0 || capacity > maximum_capacity || capacity > MAX_SNAPSHOT_LEN {
            return Err(err("snapshot capacity exceeds caller limit"));
        }
        let clock = read_u64(raw, 16)?;
        let count = read_u32(raw, 24)? as usize;
        let body_len = read_u32(raw, 28)? as usize;
        if count > 65_536 || raw.len() != 36 + body_len {
            return Err(err("snapshot count or body length is invalid"));
        }
        let body = &raw[36..];
        if crc32(body) != read_u32(raw, 32)? {
            return Err(err("snapshot CRC mismatch"));
        }
        let mut entries = BTreeMap::new();
        let mut offset = 0usize;
        for _ in 0..count {
            if body.len().saturating_sub(offset) < 36 {
                return Err(err("truncated snapshot entry"));
            }
            let mut packet_id = [0u8; 16];
            packet_id.copy_from_slice(&body[offset..offset + 16]);
            let generation = read_u32(body, offset + 16)?;
            let last_access = read_u64(body, offset + 20)?;
            let pinned = match body[offset + 28] {
                0 => false,
                1 => true,
                _ => return Err(err("invalid snapshot pinned flag")),
            };
            if body[offset + 29..offset + 32] != [0, 0, 0] {
                return Err(err("snapshot entry reserved bytes must be zero"));
            }
            let packet_len = read_u32(body, offset + 32)? as usize;
            let packet_start = offset + 36;
            let packet_end = packet_start
                .checked_add(packet_len)
                .ok_or_else(|| err("snapshot entry overflow"))?;
            if packet_end > body.len() {
                return Err(err("truncated snapshot packet"));
            }
            let packet_raw = body[packet_start..packet_end].to_vec();
            let packet = HeldContextPacket::decode(&packet_raw)?;
            if packet.packet_id != packet_id
                || packet.generation != generation
                || packet.is_pinned() != pinned
            {
                return Err(err("snapshot metadata does not match embedded packet"));
            }
            if entries
                .insert(
                    packet_id,
                    CacheEntry {
                        raw: packet_raw,
                        generation,
                        last_access,
                        pinned,
                    },
                )
                .is_some()
            {
                return Err(err("duplicate packet ID in snapshot"));
            }
            offset = packet_end;
        }
        if offset != body.len() {
            return Err(err("unclaimed bytes remain after snapshot entries"));
        }
        let used_bytes = total_bytes(&entries);
        if used_bytes > capacity {
            return Err(err("snapshot entries exceed declared capacity"));
        }
        Ok(Self {
            capacity_bytes: capacity,
            used_bytes,
            clock,
            entries,
        })
    }
}

fn total_bytes(entries: &BTreeMap<[u8; 16], CacheEntry>) -> usize {
    entries.values().map(|entry| entry.raw.len()).sum()
}

pub fn crc32(data: &[u8]) -> u32 {
    let mut crc = 0xFFFF_FFFFu32;
    for byte in data {
        crc ^= u32::from(*byte);
        for _ in 0..8 {
            let mask = 0u32.wrapping_sub(crc & 1);
            crc = (crc >> 1) ^ (0xEDB8_8320 & mask);
        }
    }
    !crc
}

fn checked_slice(data: &[u8], offset: usize, width: usize) -> Result<&[u8], PacketError> {
    let end = offset
        .checked_add(width)
        .ok_or_else(|| err("offset overflow"))?;
    data.get(offset..end)
        .ok_or_else(|| err("truncated integer field"))
}

fn read_u16(data: &[u8], offset: usize) -> Result<u16, PacketError> {
    Ok(u16::from_le_bytes(
        checked_slice(data, offset, 2)?
            .try_into()
            .expect("width checked"),
    ))
}

fn read_u32(data: &[u8], offset: usize) -> Result<u32, PacketError> {
    Ok(u32::from_le_bytes(
        checked_slice(data, offset, 4)?
            .try_into()
            .expect("width checked"),
    ))
}

fn read_i32(data: &[u8], offset: usize) -> Result<i32, PacketError> {
    Ok(i32::from_le_bytes(
        checked_slice(data, offset, 4)?
            .try_into()
            .expect("width checked"),
    ))
}

fn read_u64(data: &[u8], offset: usize) -> Result<u64, PacketError> {
    Ok(u64::from_le_bytes(
        checked_slice(data, offset, 8)?
            .try_into()
            .expect("width checked"),
    ))
}

fn put_u16(data: &mut [u8], offset: usize, value: u16) {
    data[offset..offset + 2].copy_from_slice(&value.to_le_bytes());
}

fn put_u32(data: &mut [u8], offset: usize, value: u32) {
    data[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
}

fn put_i32(data: &mut [u8], offset: usize, value: i32) {
    data[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
}

fn put_u64(data: &mut [u8], offset: usize, value: u64) {
    data[offset..offset + 8].copy_from_slice(&value.to_le_bytes());
}

#[cfg(test)]
mod tests {
    use super::*;

    fn lane(lane_id: u16, payload_size: usize, pinned: bool) -> HeldContextLane {
        HeldContextLane {
            lane_id,
            kind: LaneKind::Linguistic,
            evidence: EvidenceState::Present,
            role: LaneRole::Observed,
            flags: if pinned {
                FLAG_PINNED
            } else {
                FLAG_COMPRESSIBLE
            },
            route_q1e6: vec![-500_000, 0, 500_000],
            token_ids: vec![1, 2, 3],
            payload: vec![lane_id as u8; payload_size],
            expiry_sequence: NO_EXPIRY,
            canonical_value_id: [lane_id as u8; 32],
            source_hash: [(lane_id + 1) as u8; 32],
        }
    }

    fn packet(id: u8, generation: u32, payload_size: usize, pinned: bool) -> HeldContextPacket {
        HeldContextPacket {
            packet_id: [id; 16],
            generation,
            sequence_cutoff: 10,
            token_budget: 128,
            breath_q1e6: Q_SCALE,
            radius_q1e6: 250_000,
            flags: 0,
            lanes: vec![lane(1, payload_size, pinned)],
        }
    }

    #[test]
    fn packet_round_trip_is_exact() {
        let raw = packet(1, 2, 17, false).encode().unwrap();
        assert_eq!(
            HeldContextPacket::decode(&raw).unwrap().encode().unwrap(),
            raw
        );
    }

    #[test]
    fn corruption_is_rejected() {
        let mut raw = packet(1, 2, 17, false).encode().unwrap();
        *raw.last_mut().unwrap() ^= 1;
        assert!(HeldContextPacket::decode(&raw).is_err());
    }

    #[test]
    fn cache_evicts_least_recently_used_with_stable_ties() {
        let a = packet(1, 1, 8, false).encode().unwrap();
        let b = packet(2, 1, 8, false).encode().unwrap();
        let c = packet(3, 1, 8, false).encode().unwrap();
        let mut cache = HeldContextCache::new(a.len() + b.len()).unwrap();
        cache.insert(&a).unwrap();
        cache.insert(&b).unwrap();
        cache.get(&[1; 16]).unwrap();
        cache.insert(&c).unwrap();
        assert!(cache.contains(&[1; 16]));
        assert!(!cache.contains(&[2; 16]));
        assert!(cache.contains(&[3; 16]));
    }

    #[test]
    fn pinned_entries_make_failed_insert_transactional() {
        let pinned = packet(1, 1, 8, true).encode().unwrap();
        let next = packet(2, 1, 8, false).encode().unwrap();
        let mut cache = HeldContextCache::new(pinned.len()).unwrap();
        cache.insert(&pinned).unwrap();
        let before = cache.clone();
        assert!(cache.insert(&next).is_err());
        assert_eq!(cache, before);
    }

    #[test]
    fn stale_and_colliding_generations_are_rejected() {
        let current = packet(1, 2, 8, false).encode().unwrap();
        let stale = packet(1, 1, 8, false).encode().unwrap();
        let collision = packet(1, 2, 9, false).encode().unwrap();
        let mut cache = HeldContextCache::new(current.len() * 2).unwrap();
        cache.insert(&current).unwrap();
        assert!(cache.insert(&stale).is_err());
        assert!(cache.insert(&collision).is_err());
    }

    #[test]
    fn snapshot_round_trip_preserves_cache() {
        let a = packet(1, 1, 8, true).encode().unwrap();
        let b = packet(2, 1, 8, false).encode().unwrap();
        let mut cache = HeldContextCache::new(a.len() + b.len() + 32).unwrap();
        cache.insert(&a).unwrap();
        cache.insert(&b).unwrap();
        cache.get(&[1; 16]).unwrap();
        let snapshot = cache.snapshot().unwrap();
        let restored = HeldContextCache::restore(&snapshot, MAX_SNAPSHOT_LEN).unwrap();
        assert_eq!(restored, cache);
    }
}
