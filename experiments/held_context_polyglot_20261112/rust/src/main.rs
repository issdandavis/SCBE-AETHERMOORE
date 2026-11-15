use held_context_v1::{HeldContextCache, HeldContextPacket, MAX_SNAPSHOT_LEN};
use std::env;
use std::fs;
use std::process::ExitCode;

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().collect();
    match args.as_slice() {
        [_, command, input] if command == "validate" => {
            let raw = fs::read(input).map_err(|error| error.to_string())?;
            let packet = HeldContextPacket::decode(&raw).map_err(|error| error.to_string())?;
            println!(
                "VALID bytes={} generation={} lanes={}",
                raw.len(),
                packet.generation,
                packet.lanes.len()
            );
            Ok(())
        }
        [_, command, input, output] if command == "roundtrip" => {
            let raw = fs::read(input).map_err(|error| error.to_string())?;
            let packet = HeldContextPacket::decode(&raw).map_err(|error| error.to_string())?;
            fs::write(output, packet.encode().map_err(|error| error.to_string())?)
                .map_err(|error| error.to_string())
        }
        [_, command, input, output] if command == "cache-roundtrip" => {
            let raw = fs::read(input).map_err(|error| error.to_string())?;
            let cache = HeldContextCache::restore(&raw, MAX_SNAPSHOT_LEN).map_err(|error| error.to_string())?;
            fs::write(output, cache.snapshot().map_err(|error| error.to_string())?)
                .map_err(|error| error.to_string())
        }
        _ => Err("usage: held-context-rs validate INPUT | roundtrip INPUT OUTPUT | cache-roundtrip INPUT OUTPUT".into()),
    }
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("ERROR: {message}");
            ExitCode::FAILURE
        }
    }
}
