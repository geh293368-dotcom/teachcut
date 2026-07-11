/**
 * @file
 * @brief Native Windows presenter for retained D3D11 video surfaces.
 */

// SPDX-License-Identifier: LGPL-3.0-or-later

#ifndef OPENSHOT_D3D11_VIDEO_PRESENTER_H
#define OPENSHOT_D3D11_VIDEO_PRESENTER_H

#include <cstdint>
#include <memory>
#include <string>

namespace openshot {

class GpuFrameSurface;

class D3D11VideoPresenter {
private:
	class Implementation;
	std::unique_ptr<Implementation> implementation;

public:
	D3D11VideoPresenter();
	~D3D11VideoPresenter();

	/// Convert and scale a D3D11 decoder surface directly into a HWND swap chain.
	bool Present(const std::shared_ptr<GpuFrameSurface>& surface, uintptr_t window_address);

	/// Capture the next converted swap-chain back buffer for verification.
	void CaptureNextFrame(const std::string& path);

	/// Release the swap chain and all video-processor state.
	void Reset();
};

}

#endif
