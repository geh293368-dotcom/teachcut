/**
 * @file
 * @brief Native Windows presenter for retained D3D11 video surfaces.
 */

// SPDX-License-Identifier: LGPL-3.0-or-later

#include "D3D11VideoPresenter.h"

#include "D3D11DeviceManager.h"
#include "GpuFrame.h"

#ifdef _WIN32
	#include <algorithm>
	#include <cmath>
	#include <cstring>
	#include <mutex>
	#include <windows.h>
	#include <d3d11.h>
	#include <dxgi1_2.h>
	#include <QImage>
	#include <QString>

extern "C" {
	#include <libavutil/frame.h>
	#include <libavutil/hwcontext.h>
	#include <libavutil/hwcontext_d3d11va.h>
}
#endif

using namespace openshot;

class D3D11VideoPresenter::Implementation {
public:
#ifdef _WIN32
	HWND window = nullptr;
	ID3D11Device *device = nullptr;
	ID3D11DeviceContext *device_context = nullptr;
	ID3D11VideoDevice *video_device = nullptr;
	ID3D11VideoContext *video_context = nullptr;
	IDXGISwapChain1 *swap_chain = nullptr;
	ID3D11VideoProcessorEnumerator *processor_enumerator = nullptr;
	ID3D11VideoProcessor *processor = nullptr;
	UINT target_width = 0;
	UINT target_height = 0;
	UINT source_width = 0;
	UINT source_height = 0;
	std::recursive_mutex state_mutex;
	std::mutex capture_mutex;
	std::string capture_next_path;

	template <typename Interface>
	static void Release(Interface *&value)
	{
		if (value) {
			value->Release();
			value = nullptr;
		}
	}

	void ResetProcessor()
	{
		Release(processor);
		Release(processor_enumerator);
		source_width = 0;
		source_height = 0;
	}

	void ResetSwapChain()
	{
		ResetProcessor();
		Release(swap_chain);
		target_width = 0;
		target_height = 0;
		window = nullptr;
	}

	void Reset()
	{
		const std::lock_guard<std::recursive_mutex> state_lock(state_mutex);
		{
			const std::lock_guard<std::mutex> lock(capture_mutex);
			capture_next_path.clear();
		}
		ResetSwapChain();
		Release(video_context);
		Release(video_device);
		Release(device_context);
		Release(device);
	}

	bool EnsureDevice()
	{
		auto& manager = D3D11DeviceManager::Instance();
		if (!manager.IsReady())
			return false;
		auto *shared_device = reinterpret_cast<ID3D11Device*>(manager.DeviceAddress());
		auto *shared_context = reinterpret_cast<ID3D11DeviceContext*>(manager.DeviceContextAddress());
		if (!shared_device || !shared_context)
			return false;
		if (device == shared_device && device_context == shared_context && video_device && video_context)
			return true;

		Reset();
		device = shared_device;
		device_context = shared_context;
		device->AddRef();
		device_context->AddRef();
		if (FAILED(device->QueryInterface(__uuidof(ID3D11VideoDevice), reinterpret_cast<void**>(&video_device))))
			return false;
		if (FAILED(device_context->QueryInterface(__uuidof(ID3D11VideoContext), reinterpret_cast<void**>(&video_context))))
			return false;
		return true;
	}

	bool CreateSwapChain(HWND requested_window, UINT width, UINT height)
	{
		IDXGIDevice *dxgi_device = nullptr;
		IDXGIAdapter *adapter = nullptr;
		IDXGIFactory2 *factory = nullptr;
		HRESULT result = device->QueryInterface(__uuidof(IDXGIDevice), reinterpret_cast<void**>(&dxgi_device));
		if (SUCCEEDED(result))
			result = dxgi_device->GetAdapter(&adapter);
		if (SUCCEEDED(result))
			result = adapter->GetParent(__uuidof(IDXGIFactory2), reinterpret_cast<void**>(&factory));

		IDXGISwapChain1 *created_swap_chain = nullptr;
		if (SUCCEEDED(result)) {
			DXGI_SWAP_CHAIN_DESC1 description{};
			description.Width = width;
			description.Height = height;
			description.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
			description.Stereo = FALSE;
			description.SampleDesc.Count = 1;
			description.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
			description.BufferCount = 2;
			description.Scaling = DXGI_SCALING_STRETCH;
			description.SwapEffect = DXGI_SWAP_EFFECT_FLIP_SEQUENTIAL;
			description.AlphaMode = DXGI_ALPHA_MODE_IGNORE;
			result = factory->CreateSwapChainForHwnd(
				device,
				requested_window,
				&description,
				nullptr,
				nullptr,
				&created_swap_chain
			);
			if (SUCCEEDED(result))
				factory->MakeWindowAssociation(requested_window, DXGI_MWA_NO_ALT_ENTER);
		}

		Release(factory);
		Release(adapter);
		Release(dxgi_device);
		if (FAILED(result)) {
			Release(created_swap_chain);
			return false;
		}

		ResetSwapChain();
		swap_chain = created_swap_chain;
		window = requested_window;
		target_width = width;
		target_height = height;
		return true;
	}

	bool EnsureSwapChain(HWND requested_window, UINT width, UINT height)
	{
		if (!swap_chain || window != requested_window)
			return CreateSwapChain(requested_window, width, height);
		if (target_width == width && target_height == height)
			return true;

		ResetProcessor();
		if (FAILED(swap_chain->ResizeBuffers(0, width, height, DXGI_FORMAT_UNKNOWN, 0))) {
			ResetSwapChain();
			return CreateSwapChain(requested_window, width, height);
		}
		target_width = width;
		target_height = height;
		return true;
	}

	bool EnsureProcessor(UINT width, UINT height)
	{
		if (processor && processor_enumerator
				&& source_width == width && source_height == height)
			return true;

		ResetProcessor();
		D3D11_VIDEO_PROCESSOR_CONTENT_DESC description{};
		description.InputFrameFormat = D3D11_VIDEO_FRAME_FORMAT_PROGRESSIVE;
		description.InputFrameRate.Numerator = 30;
		description.InputFrameRate.Denominator = 1;
		description.InputWidth = width;
		description.InputHeight = height;
		description.OutputFrameRate.Numerator = 30;
		description.OutputFrameRate.Denominator = 1;
		description.OutputWidth = target_width;
		description.OutputHeight = target_height;
		description.Usage = D3D11_VIDEO_USAGE_PLAYBACK_NORMAL;
		if (FAILED(video_device->CreateVideoProcessorEnumerator(&description, &processor_enumerator)))
			return false;
		if (FAILED(video_device->CreateVideoProcessor(processor_enumerator, 0, &processor))) {
			ResetProcessor();
			return false;
		}
		source_width = width;
		source_height = height;
		return true;
	}

	void CaptureNextFrame(const std::string& path)
	{
		const std::lock_guard<std::mutex> lock(capture_mutex);
		capture_next_path = path;
	}

	std::string TakeCapturePath()
	{
		const std::lock_guard<std::mutex> lock(capture_mutex);
		std::string path = capture_next_path;
		capture_next_path.clear();
		return path;
	}

	bool CaptureBackBuffer(ID3D11Texture2D *back_buffer, const std::string& path)
	{
		if (!back_buffer || path.empty())
			return false;
		D3D11_TEXTURE2D_DESC description{};
		back_buffer->GetDesc(&description);
		description.Usage = D3D11_USAGE_STAGING;
		description.BindFlags = 0;
		description.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
		description.MiscFlags = 0;
		ID3D11Texture2D *staging = nullptr;
		if (FAILED(device->CreateTexture2D(&description, nullptr, &staging)))
			return false;
		device_context->CopyResource(staging, back_buffer);
		D3D11_MAPPED_SUBRESOURCE mapped{};
		if (FAILED(device_context->Map(staging, 0, D3D11_MAP_READ, 0, &mapped))) {
			Release(staging);
			return false;
		}

		QImage image(
			static_cast<int>(description.Width),
			static_cast<int>(description.Height),
			QImage::Format_ARGB32
		);
		const size_t row_bytes = static_cast<size_t>(description.Width) * 4;
		for (UINT row = 0; row < description.Height; ++row) {
			std::memcpy(
				image.scanLine(static_cast<int>(row)),
				static_cast<const uint8_t*>(mapped.pData) + row * mapped.RowPitch,
				row_bytes
			);
		}
		device_context->Unmap(staging, 0);
		Release(staging);
		return image.save(QString::fromStdString(path), "PNG");
	}

	bool Present(const std::shared_ptr<GpuFrameSurface>& surface, HWND requested_window)
	{
		const std::lock_guard<std::recursive_mutex> state_lock(state_mutex);
		if (!surface || !surface->IsValid() || !requested_window || !IsWindow(requested_window))
			return false;
		RECT client_rect{};
		if (!GetClientRect(requested_window, &client_rect))
			return false;
		const UINT width = static_cast<UINT>(std::max<LONG>(1, client_rect.right - client_rect.left));
		const UINT height = static_cast<UINT>(std::max<LONG>(1, client_rect.bottom - client_rect.top));
		if (!EnsureDevice() || !EnsureSwapChain(requested_window, width, height)
				|| !EnsureProcessor(static_cast<UINT>(surface->Width()), static_cast<UINT>(surface->Height())))
			return false;

		auto *texture = reinterpret_cast<ID3D11Texture2D*>(surface->TextureAddress());
		if (!texture)
			return false;
		ID3D11Device *texture_device = nullptr;
		texture->GetDevice(&texture_device);
		const bool same_device = texture_device == device;
		Release(texture_device);
		if (!same_device)
			return false;

		AVD3D11VADeviceContext *ffmpeg_device = nullptr;
		if (surface->frame && surface->frame->hw_frames_ctx) {
			auto *frames_context = reinterpret_cast<AVHWFramesContext*>(surface->frame->hw_frames_ctx->data);
			if (frames_context && frames_context->device_ctx)
				ffmpeg_device = reinterpret_cast<AVD3D11VADeviceContext*>(frames_context->device_ctx->hwctx);
		}
		if (ffmpeg_device && ffmpeg_device->lock)
			ffmpeg_device->lock(ffmpeg_device->lock_ctx);

		ID3D11VideoProcessorInputView *input_view = nullptr;
		ID3D11Texture2D *back_buffer = nullptr;
		ID3D11VideoProcessorOutputView *output_view = nullptr;
		D3D11_VIDEO_PROCESSOR_INPUT_VIEW_DESC input_description{};
		input_description.ViewDimension = D3D11_VPIV_DIMENSION_TEXTURE2D;
		input_description.Texture2D.MipSlice = 0;
		input_description.Texture2D.ArraySlice = static_cast<UINT>(surface->TextureIndex());
		HRESULT result = video_device->CreateVideoProcessorInputView(
			texture,
			processor_enumerator,
			&input_description,
			&input_view
		);
		if (SUCCEEDED(result))
			result = swap_chain->GetBuffer(0, __uuidof(ID3D11Texture2D), reinterpret_cast<void**>(&back_buffer));
		if (SUCCEEDED(result)) {
			D3D11_VIDEO_PROCESSOR_OUTPUT_VIEW_DESC output_description{};
			output_description.ViewDimension = D3D11_VPOV_DIMENSION_TEXTURE2D;
			output_description.Texture2D.MipSlice = 0;
			result = video_device->CreateVideoProcessorOutputView(
				back_buffer,
				processor_enumerator,
				&output_description,
				&output_view
			);
		}

		if (SUCCEEDED(result)) {
			const RECT source_rect{0, 0, surface->Width(), surface->Height()};
			const double scale = std::min(
				static_cast<double>(target_width) / surface->Width(),
				static_cast<double>(target_height) / surface->Height()
			);
			const LONG display_width = static_cast<LONG>(std::lround(surface->Width() * scale));
			const LONG display_height = static_cast<LONG>(std::lround(surface->Height() * scale));
			const LONG left = (static_cast<LONG>(target_width) - display_width) / 2;
			const LONG top = (static_cast<LONG>(target_height) - display_height) / 2;
			const RECT destination_rect{left, top, left + display_width, top + display_height};
			const RECT target_rect{0, 0, static_cast<LONG>(target_width), static_cast<LONG>(target_height)};

			D3D11_VIDEO_COLOR background{};
			background.RGBA.A = 1.0f;
			video_context->VideoProcessorSetOutputBackgroundColor(processor, TRUE, &background);
			video_context->VideoProcessorSetOutputTargetRect(processor, TRUE, &target_rect);
			video_context->VideoProcessorSetStreamSourceRect(processor, 0, TRUE, &source_rect);
			video_context->VideoProcessorSetStreamDestRect(processor, 0, TRUE, &destination_rect);

			D3D11_VIDEO_PROCESSOR_COLOR_SPACE input_color{};
			input_color.YCbCr_Matrix = surface->Width() >= 1280 ? 1 : 0;
			input_color.Nominal_Range = 1;
			video_context->VideoProcessorSetStreamColorSpace(processor, 0, &input_color);
			D3D11_VIDEO_PROCESSOR_COLOR_SPACE output_color{};
			output_color.RGB_Range = 0;
			output_color.Nominal_Range = 2;
			video_context->VideoProcessorSetOutputColorSpace(processor, &output_color);

			D3D11_VIDEO_PROCESSOR_STREAM stream{};
			stream.Enable = TRUE;
			stream.OutputIndex = 0;
			stream.InputFrameOrField = 0;
			stream.pInputSurface = input_view;
			result = video_context->VideoProcessorBlt(processor, output_view, 0, 1, &stream);
			const std::string capture_path = TakeCapturePath();
			if (SUCCEEDED(result) && !capture_path.empty() && !CaptureBackBuffer(back_buffer, capture_path))
				result = E_FAIL;
		}

		Release(output_view);
		Release(back_buffer);
		Release(input_view);
		if (ffmpeg_device && ffmpeg_device->unlock)
			ffmpeg_device->unlock(ffmpeg_device->lock_ctx);
		if (FAILED(result))
			return false;
		return SUCCEEDED(swap_chain->Present(0, 0));
	}
#else
	void Reset() {}
	bool Present(const std::shared_ptr<GpuFrameSurface>&, uintptr_t) { return false; }
	void CaptureNextFrame(const std::string&) {}
#endif
};

D3D11VideoPresenter::D3D11VideoPresenter()
	: implementation(new Implementation())
{
}

void D3D11VideoPresenter::CaptureNextFrame(const std::string& path)
{
	implementation->CaptureNextFrame(path);
}

D3D11VideoPresenter::~D3D11VideoPresenter()
{
	Reset();
}

bool D3D11VideoPresenter::Present(
	const std::shared_ptr<GpuFrameSurface>& surface,
	uintptr_t window_address)
{
#ifdef _WIN32
	return implementation->Present(surface, reinterpret_cast<HWND>(window_address));
#else
	return implementation->Present(surface, window_address);
#endif
}

void D3D11VideoPresenter::Reset()
{
	implementation->Reset();
}
