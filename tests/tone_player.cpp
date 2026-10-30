// Short-lived playback source for the opt-in hardware isolation test.
#define NOMINMAX
#include <windows.h>
#include <mmsystem.h>
#include <cmath>
#include <cstdlib>
#include <string>
#include <vector>

int main(int argc, char** argv) {
    if (argc < 5) return 2;
    const double frequency = std::atof(argv[1]);
    const double duration = std::atof(argv[2]);
    const double quietStart = std::atof(argv[3]);
    const double quietEnd = std::atof(argv[4]);
    if (frequency < 100 || frequency > 4000 || duration <= 0 || duration > 30) return 2;
    if (argc > 5) {
        wchar_t executable[32768]; GetModuleFileNameW(nullptr, executable, ARRAYSIZE(executable));
        std::wstring command = L"\"" + std::wstring(executable) + L"\" " +
            std::to_wstring(frequency) + L" " + std::to_wstring(duration) + L" " +
            std::to_wstring(quietStart) + L" " + std::to_wstring(quietEnd);
        STARTUPINFOW startup{}; startup.cb = sizeof(startup);
        PROCESS_INFORMATION process{};
        if (!CreateProcessW(executable, command.data(), nullptr, nullptr, FALSE, CREATE_NO_WINDOW,
                            nullptr, nullptr, &startup, &process)) return 3;
        WaitForSingleObject(process.hProcess, 35000);
        DWORD result = 1; GetExitCodeProcess(process.hProcess, &result);
        CloseHandle(process.hThread); CloseHandle(process.hProcess);
        return static_cast<int>(result);
    }
    WAVEFORMATEX format{};
    format.wFormatTag = WAVE_FORMAT_PCM; format.nChannels = 2;
    format.nSamplesPerSec = 48000; format.wBitsPerSample = 16;
    format.nBlockAlign = 4; format.nAvgBytesPerSec = 192000;
    HWAVEOUT output = nullptr;
    if (waveOutOpen(&output, WAVE_MAPPER, &format, 0, 0, CALLBACK_NULL) != MMSYSERR_NOERROR) return 4;
    std::vector<short> samples(static_cast<size_t>(48000 * duration) * 2);
    for (size_t i = 0; i < samples.size() / 2; ++i) {
        const double t = static_cast<double>(i) / 48000;
        const short value = (t >= quietStart && t < quietEnd) ? 0 :
            static_cast<short>(2600 * std::sin(6.283185307179586 * frequency * t));
        samples[i * 2] = samples[i * 2 + 1] = value;
    }
    WAVEHDR header{};
    header.lpData = reinterpret_cast<LPSTR>(samples.data());
    header.dwBufferLength = static_cast<DWORD>(samples.size() * sizeof(short));
    if (waveOutPrepareHeader(output, &header, sizeof(header)) != MMSYSERR_NOERROR) return 5;
    if (waveOutWrite(output, &header, sizeof(header)) != MMSYSERR_NOERROR) return 6;
    while (!(header.dwFlags & WHDR_DONE)) Sleep(10);
    waveOutUnprepareHeader(output, &header, sizeof(header));
    waveOutClose(output);
    return 0;
}
