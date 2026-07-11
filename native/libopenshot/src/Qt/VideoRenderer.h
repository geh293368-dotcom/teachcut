/**
 * @file
 * @brief Header file for Video Renderer class
 * @author Jonathan Thomas <jonathan@openshot.org>
 *
 * @ref License
 */

// Copyright (c) 2008-2019 OpenShot Studios, LLC
//
// SPDX-License-Identifier: LGPL-3.0-or-later

#ifndef OPENSHOT_VIDEO_RENDERER_H
#define OPENSHOT_VIDEO_RENDERER_H

#include "../RendererBase.h"
#include <cstdint>
#include <atomic>
#include <QtCore/QMetaObject>
#include <QtCore/QObject>
#include <QtGui/QImage>
#include <memory>


class QPainter;
class QWidget;

namespace openshot {
class D3D11VideoPresenter;
class GpuFrameSurface;
}

class VideoRenderer : public QObject, public openshot::RendererBase
{
    Q_OBJECT

public:
    VideoRenderer(QObject *parent = 0);
    ~VideoRenderer();

    /// Override QWidget which needs to be painted
    void OverrideWidget(uintptr_t qwidget_address);

    /// Return direct-present and fallback counters as JSON.
    std::string PerformanceMetricsJson() const;

    /// Reset direct-present and fallback counters.
    void ResetPerformanceMetrics();

    /// Save the next converted D3D11 back buffer to an image file.
    void CaptureNextFrame(const std::string& path);

signals:
    void present(const QImage &image);

protected:
    //void render(openshot::OSPixelFormat format, int width, int height, int bytesPerLine, unsigned char *data);
    void render(std::shared_ptr<QImage> image);
    bool renderGpu(std::shared_ptr<openshot::GpuFrameSurface> surface) override;

private slots:

private:
    QWidget* override_widget;
    QMetaObject::Connection override_present_connection;
    std::unique_ptr<openshot::D3D11VideoPresenter> d3d11_presenter;
    std::atomic<uintptr_t> target_window{0};
    std::atomic<uint64_t> metric_direct_presents{0};
    std::atomic<uint64_t> metric_fallback_presents{0};
    std::atomic<uint64_t> metric_present_failures{0};
    std::atomic<uint64_t> metric_direct_present_nanoseconds{0};
};

#endif //OPENSHOT_VIDEO_RENDERER_H
