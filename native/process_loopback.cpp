// Native Windows process-loopback bridge. Only output streams are opened.
#define NOMINMAX
#include <windows.h>
#include <audioclient.h>
#include <audioclientactivationparams.h>
#include <mmdeviceapi.h>
#include <audiopolicy.h>
#include <tlhelp32.h>
#include <wrl.h>
#include <wrl/implements.h>
#include <algorithm>
#include <map>
#include <memory>
#include <string>
#include <vector>

using Microsoft::WRL::ComPtr;
using Microsoft::WRL::Make;
using Microsoft::WRL::RuntimeClass;
using Microsoft::WRL::RuntimeClassFlags;
using Microsoft::WRL::ClassicCom;
using Microsoft::WRL::FtmBase;

struct AppInfo {
    DWORD pid;
    DWORD active;
    ULONGLONG created;
    wchar_t path[1024];
    wchar_t name[260];
};

static ULONGLONG Created(HANDLE process) {
    FILETIME creation{}, exit{}, kernel{}, user{};
    if (!GetProcessTimes(process, &creation, &exit, &kernel, &user)) return 0;
    return (static_cast<ULONGLONG>(creation.dwHighDateTime) << 32) | creation.dwLowDateTime;
}

static std::wstring ProcessPath(DWORD pid) {
    HANDLE process = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
    if (!process) return {};
    wchar_t path[32768]; DWORD size = ARRAYSIZE(path);
    const bool success = QueryFullProcessImageNameW(process, 0, path, &size) != FALSE;
    CloseHandle(process);
    return success ? std::wstring(path, size) : std::wstring{};
}

static DWORD RootProcess(DWORD pid, const std::map<DWORD, DWORD>& parents) {
    const auto path = ProcessPath(pid);
    if (path.empty()) return pid;
    // Chromium/Electron put the actual audio session in a child process.
    // Walk only ancestors of the same executable; never capture the shell.
    for (int depth = 0; depth < 32; ++depth) {
        auto parent = parents.find(pid);
        if (parent == parents.end() || !parent->second || parent->second == pid) break;
        const auto parentPath = ProcessPath(parent->second);
        if (parentPath.empty() || _wcsicmp(path.c_str(), parentPath.c_str())) break;
        // Parent PID may have been recycled since this process was created.
        HANDLE childHandle = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
        HANDLE parentHandle = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, parent->second);
        const auto childTime = childHandle ? Created(childHandle) : 0;
        const auto parentTime = parentHandle ? Created(parentHandle) : 0;
        if (childHandle) CloseHandle(childHandle);
        if (parentHandle) CloseHandle(parentHandle);
        if (!childTime || !parentTime || parentTime > childTime) break;
        pid = parent->second;
    }
    return pid;
}

extern "C" __declspec(dllexport) HRESULT __cdecl zal_list_apps(AppInfo* output, UINT capacity, UINT* count) {
    if (!count || (!output && capacity)) return E_POINTER;
    *count = 0;
    const HRESULT init = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    if (FAILED(init) && init != RPC_E_CHANGED_MODE) return init;
    HRESULT result = S_OK;
    {
        std::map<DWORD, DWORD> parents;
        HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
        if (snapshot != INVALID_HANDLE_VALUE) {
            PROCESSENTRY32W entry{}; entry.dwSize = sizeof(entry);
            if (Process32FirstW(snapshot, &entry)) do {
                parents[entry.th32ProcessID] = entry.th32ParentProcessID;
            } while (Process32NextW(snapshot, &entry));
            CloseHandle(snapshot);
        }
        std::map<DWORD, AppInfo> apps;
        ComPtr<IMMDeviceEnumerator> enumerator;
        result = CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr, CLSCTX_ALL, IID_PPV_ARGS(&enumerator));
        ComPtr<IMMDeviceCollection> devices;
        if (SUCCEEDED(result)) result = enumerator->EnumAudioEndpoints(eRender, DEVICE_STATE_ACTIVE, &devices);
        UINT deviceCount = 0;
        if (SUCCEEDED(result)) result = devices->GetCount(&deviceCount);
        for (UINT d = 0; SUCCEEDED(result) && d < deviceCount; ++d) {
            ComPtr<IMMDevice> device;
            ComPtr<IAudioSessionManager2> manager;
            ComPtr<IAudioSessionEnumerator> sessions;
            if (FAILED(devices->Item(d, &device)) ||
                FAILED(device->Activate(__uuidof(IAudioSessionManager2), CLSCTX_ALL, nullptr, &manager)) ||
                FAILED(manager->GetSessionEnumerator(&sessions))) continue;
            int sessionCount = 0; sessions->GetCount(&sessionCount);
            for (int s = 0; s < sessionCount; ++s) {
                ComPtr<IAudioSessionControl> control;
                ComPtr<IAudioSessionControl2> control2;
                DWORD pid = 0; AudioSessionState state{};
                if (FAILED(sessions->GetSession(s, &control)) || FAILED(control.As(&control2)) ||
                    FAILED(control2->GetProcessId(&pid)) || !pid ||
                    FAILED(control->GetState(&state)) || state == AudioSessionStateExpired) continue;
                pid = RootProcess(pid, parents);
                const auto path = ProcessPath(pid);
                if (path.empty() || path.size() >= 1024) continue;
                auto& app = apps[pid];
                app.pid = pid;
                app.active |= state == AudioSessionStateActive ? 1 : 0;
                HANDLE process = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
                if (process) { app.created = Created(process); CloseHandle(process); }
                wcsncpy_s(app.path, path.c_str(), _TRUNCATE);
                auto name = path.substr(path.find_last_of(L"\\/") + 1);
                if (name.size() > 4 && !_wcsicmp(name.c_str() + name.size() - 4, L".exe")) name.resize(name.size() - 4);
                wcsncpy_s(app.name, name.c_str(), _TRUNCATE);
            }
        }
        for (const auto& pair : apps) {
            if (*count >= capacity) { result = HRESULT_FROM_WIN32(ERROR_INSUFFICIENT_BUFFER); break; }
            output[(*count)++] = pair.second;
        }
    }
    if (SUCCEEDED(init)) CoUninitialize();
    return result;
}

class Activation final : public RuntimeClass<RuntimeClassFlags<ClassicCom>, FtmBase, IActivateAudioInterfaceCompletionHandler> {
public:
    HANDLE done = CreateEventW(nullptr, TRUE, FALSE, nullptr);
    HRESULT result = E_PENDING;
    ComPtr<IAudioClient> client;
    AUDIOCLIENT_ACTIVATION_PARAMS params{};
    PROPVARIANT variant{};
    ~Activation() { if (done) CloseHandle(done); }
    STDMETHOD(ActivateCompleted)(IActivateAudioInterfaceAsyncOperation* operation) override {
        HRESULT activated = E_FAIL;
        ComPtr<IUnknown> unknown;
        result = operation->GetActivateResult(&activated, &unknown);
        if (SUCCEEDED(result)) result = activated;
        if (SUCCEEDED(result)) result = unknown.As(&client);
        SetEvent(done);
        return S_OK;
    }
};

class Capture final {
public:
    bool com = false;
    bool started = false;
    HANDLE ready = nullptr;
    HANDLE process = nullptr;
    ComPtr<IAudioClient> client;
    ComPtr<IAudioCaptureClient> capture;
    ComPtr<Activation> activation;

    HRESULT Initialize(DWORD pid, ULONGLONG expectedCreation) {
        HRESULT hr = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
        if (FAILED(hr)) return hr;
        com = true;
        process = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, FALSE, pid);
        if (!process) return HRESULT_FROM_WIN32(GetLastError());
        if (!expectedCreation || Created(process) != expectedCreation)
            return HRESULT_FROM_WIN32(ERROR_PROCESS_ABORTED);
        activation = Make<Activation>();
        if (!activation || !activation->done) return E_OUTOFMEMORY;
        activation->params.ActivationType = AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK;
        activation->params.ProcessLoopbackParams.TargetProcessId = pid;
        activation->params.ProcessLoopbackParams.ProcessLoopbackMode = PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE;
        activation->variant.vt = VT_BLOB;
        activation->variant.blob.cbSize = sizeof(activation->params);
        activation->variant.blob.pBlobData = reinterpret_cast<BYTE*>(&activation->params);
        ComPtr<IActivateAudioInterfaceAsyncOperation> operation;
        hr = ActivateAudioInterfaceAsync(VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK, __uuidof(IAudioClient),
            &activation->variant, activation.Get(), &operation);
        if (FAILED(hr)) return hr;
        if (WaitForSingleObject(activation->done, 10000) != WAIT_OBJECT_0) return HRESULT_FROM_WIN32(ERROR_TIMEOUT);
        if (FAILED(activation->result)) return activation->result;
        client = activation->client;
        WAVEFORMATEX format{};
        format.wFormatTag = WAVE_FORMAT_PCM;
        format.nChannels = 2; format.nSamplesPerSec = 48000; format.wBitsPerSample = 16;
        format.nBlockAlign = 4; format.nAvgBytesPerSec = 192000;
        hr = client->Initialize(AUDCLNT_SHAREMODE_SHARED,
            AUDCLNT_STREAMFLAGS_LOOPBACK | AUDCLNT_STREAMFLAGS_EVENTCALLBACK | AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM,
            0, 0, &format, nullptr);
        if (FAILED(hr)) return hr;
        hr = client->GetService(IID_PPV_ARGS(&capture));
        if (FAILED(hr)) return hr;
        ready = CreateEventW(nullptr, FALSE, FALSE, nullptr);
        if (!ready) return HRESULT_FROM_WIN32(GetLastError());
        hr = client->SetEventHandle(ready);
        if (FAILED(hr)) return hr;
        hr = client->Start();
        started = SUCCEEDED(hr);
        return hr;
    }

    HRESULT Read(short* destination, UINT capacity, UINT* count, DWORD timeout) {
        if (!destination || !count || !capacity) return E_POINTER;
        *count = 0;
        if (WaitForSingleObject(process, 0) == WAIT_OBJECT_0) return HRESULT_FROM_WIN32(ERROR_PROCESS_ABORTED);
        UINT available = 0;
        HRESULT hr = capture->GetNextPacketSize(&available);
        if (FAILED(hr)) return hr;
        if (!available) {
            const DWORD wait = WaitForSingleObject(ready, std::min(timeout, 100UL));
            if (wait == WAIT_TIMEOUT) return S_OK;
            if (wait != WAIT_OBJECT_0) return HRESULT_FROM_WIN32(GetLastError());
        }
        for (;;) {
            hr = capture->GetNextPacketSize(&available);
            if (FAILED(hr) || !available) return hr;
            if (available > capacity - *count) return *count ? S_OK : HRESULT_FROM_WIN32(ERROR_INSUFFICIENT_BUFFER);
            BYTE* data = nullptr; UINT frames = 0; DWORD flags = 0;
            hr = capture->GetBuffer(&data, &frames, &flags, nullptr, nullptr);
            if (FAILED(hr)) return hr;
            if (flags & AUDCLNT_BUFFERFLAGS_SILENT) ZeroMemory(destination + *count * 2, frames * 4);
            else memcpy(destination + *count * 2, data, frames * 4);
            *count += frames;
            hr = capture->ReleaseBuffer(frames);
            if (FAILED(hr) || *count == capacity) return hr;
        }
    }

    ~Capture() {
        if (started && client) client->Stop();
        capture.Reset(); client.Reset(); activation.Reset();
        if (ready) CloseHandle(ready);
        if (process) CloseHandle(process);
        if (com) CoUninitialize();
    }
};

extern "C" __declspec(dllexport) void* __cdecl zal_capture_create(DWORD pid, ULONGLONG created, HRESULT* result) {
    if (!result) return nullptr;
    try {
        auto capture = std::make_unique<Capture>();
        *result = capture->Initialize(pid, created);
        return SUCCEEDED(*result) ? capture.release() : nullptr;
    } catch (...) { *result = E_OUTOFMEMORY; return nullptr; }
}
extern "C" __declspec(dllexport) HRESULT __cdecl zal_capture_read(void* handle, short* samples, UINT capacity, UINT* count, DWORD timeout) {
    if (!handle) return E_HANDLE;
    return static_cast<Capture*>(handle)->Read(samples, capacity, count, timeout);
}
extern "C" __declspec(dllexport) void __cdecl zal_capture_destroy(void* handle) {
    delete static_cast<Capture*>(handle);
}
