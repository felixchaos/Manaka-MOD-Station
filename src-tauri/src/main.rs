// Prevents an extra terminal window when the dev runner launches the app on Windows.
#![cfg_attr(target_os = "windows", windows_subsystem = "windows")]

fn main() {
    manaka_mod_station_lib::run()
}
