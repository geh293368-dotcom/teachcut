/**
 * @file
 * @brief GPU-backed frame surface implementation.
 */

// SPDX-License-Identifier: LGPL-3.0-or-later

#include "GpuFrame.h"

#include <chrono>
#include <QImage>

extern "C" {
	#include <libavutil/frame.h>
	#include <libavutil/hwcontext.h>
	#include <libavutil/pixfmt.h>
	#include <libswscale/swscale.h>
}

using namespace openshot;

GpuFrameSurface::GpuFrameSurface(const AVFrame *source_frame)
{
	if (!source_frame)
		return;
	frame = av_frame_clone(source_frame);
	if (!frame)
		return;
	width = frame->width;
	height = frame->height;
	texture_index = static_cast<int>(reinterpret_cast<intptr_t>(frame->data[1]));
}

GpuFrameSurface::~GpuFrameSurface()
{
	if (frame)
		av_frame_free(&frame);
}

std::shared_ptr<GpuFrameSurface> GpuFrameSurface::CreateFromD3D11Frame(const AVFrame *source_frame)
{
	if (!source_frame || source_frame->format != AV_PIX_FMT_D3D11 || !source_frame->data[0])
		return nullptr;
	auto surface = std::shared_ptr<GpuFrameSurface>(new GpuFrameSurface(source_frame));
	return surface->IsValid() ? surface : nullptr;
}

bool GpuFrameSurface::IsValid() const
{
	return frame && frame->format == AV_PIX_FMT_D3D11 && frame->data[0] && width > 0 && height > 0;
}

uintptr_t GpuFrameSurface::TextureAddress() const
{
	return IsValid() ? reinterpret_cast<uintptr_t>(frame->data[0]) : 0;
}

std::shared_ptr<QImage> GpuFrameSurface::DownloadToImage() const
{
	if (!IsValid())
		return nullptr;

	const auto started = std::chrono::steady_clock::now();
	download_count.fetch_add(1);
	AVFrame *software_frame = av_frame_alloc();
	if (!software_frame)
		return nullptr;

	std::shared_ptr<QImage> result;
	if (av_hwframe_transfer_data(software_frame, frame, 0) >= 0) {
		const int output_width = software_frame->width > 0 ? software_frame->width : width;
		const int output_height = software_frame->height > 0 ? software_frame->height : height;
		SwsContext *converter = sws_getContext(
			output_width,
			output_height,
			static_cast<AVPixelFormat>(software_frame->format),
			output_width,
			output_height,
			AV_PIX_FMT_RGBA,
			SWS_FAST_BILINEAR,
			nullptr,
			nullptr,
			nullptr
		);
		if (converter) {
			auto image = std::make_shared<QImage>(
				output_width,
				output_height,
				QImage::Format_RGBA8888_Premultiplied
			);
			uint8_t *destination_data[4] = { image->bits(), nullptr, nullptr, nullptr };
			int destination_linesize[4] = { image->bytesPerLine(), 0, 0, 0 };
			const int converted_lines = sws_scale(
				converter,
				software_frame->data,
				software_frame->linesize,
				0,
				output_height,
				destination_data,
				destination_linesize
			);
			if (converted_lines > 0)
				result = image;
			sws_freeContext(converter);
		}
	}
	av_frame_free(&software_frame);

	const auto elapsed = std::chrono::duration_cast<std::chrono::nanoseconds>(
		std::chrono::steady_clock::now() - started
	).count();
	download_nanoseconds.fetch_add(static_cast<uint64_t>(elapsed));
	return result;
}
