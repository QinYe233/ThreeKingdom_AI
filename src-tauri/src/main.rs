// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::TcpListener;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::Manager;

// Windows 平台常量：CREATE_NO_WINDOW（仅 release 模式使用）
#[cfg(all(target_os = "windows", not(debug_assertions)))]
const CREATE_NO_WINDOW: u32 = 0x08000000;

// 全局存储后端进程和端口
static BACKEND_PROCESS: Mutex<Option<Child>> = Mutex::new(None);
static BACKEND_PORT: Mutex<Option<u16>> = Mutex::new(None);

/// 查找可用端口，从 start 开始尝试
fn find_free_port(start: u16, end: u16) -> Option<u16> {
    for port in start..=end {
        if TcpListener::bind(("127.0.0.1", port)).is_ok() {
            return Some(port);
        }
    }
    None
}

// Tauri 命令：获取后端 API 地址
#[tauri::command]
fn get_api_base() -> String {
    let port = BACKEND_PORT.lock().unwrap();
    match *port {
        Some(p) => format!("http://127.0.0.1:{}/api", p),
        None => "http://127.0.0.1:8000/api".to_string(),
    }
}

// Tauri 命令：退出应用（释放所有资源并关闭进程）
#[tauri::command]
fn exit_app() {
    stop_backend();
    std::process::exit(0);
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .invoke_handler(tauri::generate_handler![get_api_base, exit_app])
        .setup(|app| {
            #[cfg(debug_assertions)]
            {
                let window = app.get_webview_window("main").unwrap();
                window.open_devtools();
            }

            // 查找可用端口
            let port = find_free_port(8000, 8099).expect("No available port in range 8000-8099");
            *BACKEND_PORT.lock().unwrap() = Some(port);
            println!("Using port: {}", port);

            // 启动后端
            let handle = app.handle().clone();
            start_backend(&handle, port);

            // 生产模式：通过健康检查确认后端就绪后进入全屏
            #[cfg(not(debug_assertions))]
            {
                let app_handle = app.handle().clone();
                std::thread::spawn(move || {
                    let health_url = format!("http://127.0.0.1:{}/api/ai/status", port);
                    let client = reqwest::blocking::Client::builder()
                        .timeout(std::time::Duration::from_secs(2))
                        .build()
                        .unwrap_or_default();

                    let mut ready = false;
                    for _ in 0..30 {
                        std::thread::sleep(std::time::Duration::from_millis(500));
                        if let Ok(resp) = client.get(&health_url).send() {
                            if resp.status().is_success() {
                                ready = true;
                                break;
                            }
                        }
                    }

                    if ready {
                        if let Some(window) = app_handle.get_webview_window("main") {
                            let _ = window.set_fullscreen(true);
                            let _ = window.set_focus();
                        }
                    }
                });
            }

            Ok(())
        })
        .on_window_event(|_window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                stop_backend();
                std::process::exit(0);
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn start_backend(app: &tauri::AppHandle, port: u16) {
    #[cfg(debug_assertions)]
    {
        start_backend_dev(port);
        let _ = app; // suppress unused warning in dev
    }

    #[cfg(not(debug_assertions))]
    {
        start_backend_prod(app, port);
    }
}

#[cfg(debug_assertions)]
fn start_backend_dev(port: u16) {
    let python_exe = find_python();
    // 当前目录是 src-tauri，需要向上一级找到项目根目录
    let current_dir = std::env::current_dir().expect("Failed to get current directory");
    let backend_dir = current_dir.parent()
        .expect("No parent directory")
        .join("backend");

    println!("Starting backend (dev mode) on port {} from: {:?}", port, backend_dir);

    let child = Command::new(&python_exe)
        .args([
            "-m", "uvicorn",
            "app.main:app",
            "--host", "127.0.0.1",
            "--port", &port.to_string(),
        ])
        .current_dir(&backend_dir)
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .spawn()
        .expect("Failed to start backend server");

    *BACKEND_PROCESS.lock().unwrap() = Some(child);
    std::thread::sleep(std::time::Duration::from_secs(2));
}

#[cfg(not(debug_assertions))]
fn start_backend_prod(app: &tauri::AppHandle, port: u16) {
    #[cfg(target_os = "windows")]
    use std::os::windows::process::CommandExt;

    let resource_dir = app.path().resource_dir().expect("Failed to get resource dir");

    let target_triple = std::env::consts::ARCH.to_string() + "-pc-windows-msvc";
    let backend_exe = resource_dir.join(format!("binaries/sanguo-backend-{}.exe", target_triple));

    if backend_exe.exists() {
        println!("Starting backend (prod mode) on port {}: {:?}", port, backend_exe);

        #[cfg(target_os = "windows")]
        let child = Command::new(&backend_exe)
            .args([
                "--host", "127.0.0.1",
                "--port", &port.to_string(),
            ])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .creation_flags(CREATE_NO_WINDOW)
            .spawn()
            .expect("Failed to start backend server");

        #[cfg(not(target_os = "windows"))]
        let child = Command::new(&backend_exe)
            .args([
                "--host", "127.0.0.1",
                "--port", &port.to_string(),
            ])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("Failed to start backend server");

        *BACKEND_PROCESS.lock().unwrap() = Some(child);
    } else {
        eprintln!("Backend executable not found: {:?}", backend_exe);
        eprintln!("Please reinstall the application.");
    }
}

fn stop_backend() {
    if let Ok(mut process) = BACKEND_PROCESS.lock() {
        if let Some(mut child) = process.take() {
            let _ = child.kill();
            let _ = child.wait();
            println!("Backend server stopped");
        }
    }
}

#[cfg(debug_assertions)]
fn find_python() -> String {
    let candidates = ["python", "python3", "python.exe", "python3.exe"];

    for candidate in candidates {
        if Command::new(candidate)
            .arg("--version")
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .is_ok()
        {
            return candidate.to_string();
        }
    }

    "python".to_string()
}
