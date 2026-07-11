/**
 * @file
 * @brief Shared Windows D3D11 device used by decode, preview, and encoding.
 */

// SPDX-License-Identifier: LGPL-3.0-or-later

#ifndef OPENSHOT_D3D11_DEVICE_MANAGER_H
#define OPENSHOT_D3D11_DEVICE_MANAGER_H

#include <cstdint>
#include <mutex>
#include <string>

struct AVBufferRef;

#ifdef _WIN32
struct ID3D11Device;
struct ID3D11DeviceContext;
#endif

namespace openshot {

class D3D11DeviceManager {
private:
	std::recursive_mutex mutex;
	int adapter_index = -1;
	std::string adapter_name;
	std::string adapter_luid;

#ifdef _WIN32
	ID3D11Device *device = nullptr;
	ID3D11DeviceContext *device_context = nullptr;
	bool CreateDeviceLocked(int requested_adapter);
	void ReleaseDeviceLocked();
#endif

	D3D11DeviceManager() = default;
	D3D11DeviceManager(const D3D11DeviceManager&) = delete;
	D3D11DeviceManager& operator=(const D3D11DeviceManager&) = delete;

public:
	~D3D11DeviceManager();

	static D3D11DeviceManager& Instance();

	/// Create the shared device when necessary and return whether it is ready.
	bool EnsureDevice(int requested_adapter = 0);

	/// Create an FFmpeg D3D11VA device context which references the shared device.
	AVBufferRef *CreateFFmpegDeviceContext(int requested_adapter = 0);

	bool IsReady();
	int AdapterIndex();
	std::string AdapterName();
	std::string AdapterLuid();
	uintptr_t DeviceAddress();
	uintptr_t DeviceContextAddress();
};

}

#endif
