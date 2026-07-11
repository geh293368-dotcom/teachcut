/**
 * @file
 * @brief Shared Windows D3D11 device implementation.
 */

// SPDX-License-Identifier: LGPL-3.0-or-later

#include "D3D11DeviceManager.h"

#ifdef _WIN32
	#include <windows.h>
	#include <d3d11.h>
	#include <dxgi1_2.h>
	#include <iomanip>
	#include <iterator>
	#include <sstream>

extern "C" {
	#include <libavutil/buffer.h>
	#include <libavutil/hwcontext.h>
	#include <libavutil/hwcontext_d3d11va.h>
}
#endif

using namespace openshot;

namespace {
#ifdef _WIN32
std::string WideToUtf8(const wchar_t *value)
{
	if (!value || !*value)
		return "";
	const int size = WideCharToMultiByte(CP_UTF8, 0, value, -1, nullptr, 0, nullptr, nullptr);
	if (size <= 1)
		return "";
	std::string result(static_cast<size_t>(size), '\0');
	WideCharToMultiByte(CP_UTF8, 0, value, -1, result.data(), size, nullptr, nullptr);
	result.pop_back();
	return result;
}

std::string FormatLuid(const LUID& luid)
{
	std::ostringstream stream;
	stream << std::hex << std::setfill('0')
		   << std::setw(8) << static_cast<uint32_t>(luid.HighPart)
		   << ':' << std::setw(8) << luid.LowPart;
	return stream.str();
}
#endif
}

D3D11DeviceManager& D3D11DeviceManager::Instance()
{
	static D3D11DeviceManager instance;
	return instance;
}

D3D11DeviceManager::~D3D11DeviceManager()
{
#ifdef _WIN32
	const std::lock_guard<std::recursive_mutex> lock(mutex);
	ReleaseDeviceLocked();
#endif
}

#ifdef _WIN32
void D3D11DeviceManager::ReleaseDeviceLocked()
{
	if (device_context) {
		device_context->Release();
		device_context = nullptr;
	}
	if (device) {
		device->Release();
		device = nullptr;
	}
	adapter_index = -1;
	adapter_name.clear();
	adapter_luid.clear();
}

bool D3D11DeviceManager::CreateDeviceLocked(int requested_adapter)
{
	ReleaseDeviceLocked();

	IDXGIFactory1 *factory = nullptr;
	IDXGIAdapter1 *adapter = nullptr;
	DXGI_ADAPTER_DESC1 adapter_desc{};
	if (SUCCEEDED(CreateDXGIFactory1(__uuidof(IDXGIFactory1), reinterpret_cast<void**>(&factory)))) {
		int usable_index = 0;
		for (UINT index = 0; factory->EnumAdapters1(index, &adapter) != DXGI_ERROR_NOT_FOUND; ++index) {
			adapter->GetDesc1(&adapter_desc);
			if (adapter_desc.Flags & DXGI_ADAPTER_FLAG_SOFTWARE) {
				adapter->Release();
				adapter = nullptr;
				continue;
			}
			if (usable_index++ == requested_adapter)
				break;
			adapter->Release();
			adapter = nullptr;
		}
		factory->Release();
	}

	const D3D_FEATURE_LEVEL requested_levels[] = {
		D3D_FEATURE_LEVEL_11_1,
		D3D_FEATURE_LEVEL_11_0,
		D3D_FEATURE_LEVEL_10_1,
		D3D_FEATURE_LEVEL_10_0,
	};
	D3D_FEATURE_LEVEL created_level = D3D_FEATURE_LEVEL_10_0;
	const UINT flags = D3D11_CREATE_DEVICE_BGRA_SUPPORT | D3D11_CREATE_DEVICE_VIDEO_SUPPORT;
	HRESULT result = D3D11CreateDevice(
		adapter,
		adapter ? D3D_DRIVER_TYPE_UNKNOWN : D3D_DRIVER_TYPE_HARDWARE,
		nullptr,
		flags,
		requested_levels,
		static_cast<UINT>(std::size(requested_levels)),
		D3D11_SDK_VERSION,
		&device,
		&created_level,
		&device_context
	);
	if (adapter)
		adapter->Release();
	if (FAILED(result)) {
		ReleaseDeviceLocked();
		return false;
	}

	adapter_index = requested_adapter;
	adapter_name = WideToUtf8(adapter_desc.Description);
	adapter_luid = FormatLuid(adapter_desc.AdapterLuid);
	return true;
}
#endif

bool D3D11DeviceManager::EnsureDevice(int requested_adapter)
{
#ifdef _WIN32
	const std::lock_guard<std::recursive_mutex> lock(mutex);
	if (device && adapter_index == requested_adapter)
		return true;
	return CreateDeviceLocked(requested_adapter);
#else
	(void) requested_adapter;
	return false;
#endif
}

AVBufferRef *D3D11DeviceManager::CreateFFmpegDeviceContext(int requested_adapter)
{
#ifdef _WIN32
	const std::lock_guard<std::recursive_mutex> lock(mutex);
	if ((!device || adapter_index != requested_adapter) && !CreateDeviceLocked(requested_adapter))
		return nullptr;

	AVBufferRef *reference = av_hwdevice_ctx_alloc(AV_HWDEVICE_TYPE_D3D11VA);
	if (!reference)
		return nullptr;
	auto *hardware_context = reinterpret_cast<AVHWDeviceContext*>(reference->data);
	auto *d3d11_context = reinterpret_cast<AVD3D11VADeviceContext*>(hardware_context->hwctx);
	device->AddRef();
	d3d11_context->device = device;
	if (av_hwdevice_ctx_init(reference) < 0) {
		av_buffer_unref(&reference);
		return nullptr;
	}
	return reference;
#else
	(void) requested_adapter;
	return nullptr;
#endif
}

bool D3D11DeviceManager::IsReady()
{
	const std::lock_guard<std::recursive_mutex> lock(mutex);
#ifdef _WIN32
	return device != nullptr;
#else
	return false;
#endif
}

int D3D11DeviceManager::AdapterIndex()
{
	const std::lock_guard<std::recursive_mutex> lock(mutex);
	return adapter_index;
}

std::string D3D11DeviceManager::AdapterName()
{
	const std::lock_guard<std::recursive_mutex> lock(mutex);
	return adapter_name;
}

std::string D3D11DeviceManager::AdapterLuid()
{
	const std::lock_guard<std::recursive_mutex> lock(mutex);
	return adapter_luid;
}

uintptr_t D3D11DeviceManager::DeviceAddress()
{
	const std::lock_guard<std::recursive_mutex> lock(mutex);
#ifdef _WIN32
	return reinterpret_cast<uintptr_t>(device);
#else
	return 0;
#endif
}

uintptr_t D3D11DeviceManager::DeviceContextAddress()
{
	const std::lock_guard<std::recursive_mutex> lock(mutex);
#ifdef _WIN32
	return reinterpret_cast<uintptr_t>(device_context);
#else
	return 0;
#endif
}
