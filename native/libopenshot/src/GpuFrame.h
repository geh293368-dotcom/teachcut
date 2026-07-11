/**
 * @file
 * @brief GPU-backed frame surface with lazy CPU materialization.
 */

// SPDX-License-Identifier: LGPL-3.0-or-later

#ifndef OPENSHOT_GPU_FRAME_H
#define OPENSHOT_GPU_FRAME_H

#include <atomic>
#include <cstdint>
#include <memory>

class QImage;
struct AVFrame;

namespace openshot {

class D3D11VideoPresenter;

class GpuFrameSurface {
private:
	AVFrame *frame = nullptr;
	int width = 0;
	int height = 0;
	int texture_index = 0;
	mutable std::atomic<uint64_t> download_count{0};
	mutable std::atomic<uint64_t> download_nanoseconds{0};

	explicit GpuFrameSurface(const AVFrame *source_frame);
	friend class D3D11VideoPresenter;

public:
	~GpuFrameSurface();

	static std::shared_ptr<GpuFrameSurface> CreateFromD3D11Frame(const AVFrame *source_frame);
	std::shared_ptr<QImage> DownloadToImage() const;

	bool IsValid() const;
	int Width() const { return width; }
	int Height() const { return height; }
	int TextureIndex() const { return texture_index; }
	uintptr_t TextureAddress() const;
	uint64_t DownloadCount() const { return download_count.load(); }
	uint64_t DownloadNanoseconds() const { return download_nanoseconds.load(); }
};

}

#endif
