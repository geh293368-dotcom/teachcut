/**
 * @file
 * @brief Source file for VideoRenderer class
 * @author Jonathan Thomas <jonathan@openshot.org>
 *
 * @ref License
 */

// Copyright (c) 2008-2019 OpenShot Studios, LLC
//
// SPDX-License-Identifier: LGPL-3.0-or-later

#include "VideoRenderer.h"
#include "D3D11VideoPresenter.h"
#include "GpuFrame.h"
#include "Json.h"
#include "Settings.h"
#include <chrono>
#include <QtCore/QMetaObject>
#include <QtWidgets/QWidget>

VideoRenderer::VideoRenderer(QObject *parent)
    : QObject(parent)
    , override_widget(nullptr)
    , d3d11_presenter(new openshot::D3D11VideoPresenter())
{
}

VideoRenderer::~VideoRenderer()
{
    if (d3d11_presenter)
        d3d11_presenter->Reset();
}

/// Override QWidget which needs to be painted
void VideoRenderer::OverrideWidget(uintptr_t qwidget_address)
{
    if (override_present_connection)
        QObject::disconnect(override_present_connection);

    // re-cast QWidget pointer (long) as an actual QWidget
    override_widget = reinterpret_cast<QWidget*>(qwidget_address);
    if (!override_widget) {
        target_window.store(0);
        if (d3d11_presenter)
            d3d11_presenter->Reset();
        return;
    }

#ifdef _WIN32
    auto *settings = openshot::Settings::Instance();
    if (settings->ENABLE_D3D11_ZERO_COPY && settings->ENABLE_D3D11_DIRECT_PRESENT)
        target_window.store(static_cast<uintptr_t>(override_widget->winId()));
    else
        target_window.store(0);
#else
    target_window.store(0);
#endif

    override_present_connection = QObject::connect(
        this, &VideoRenderer::present,
        override_widget,
        [widget = override_widget](const QImage &image) {
            QMetaObject::invokeMethod(
                widget, "present",
                Qt::DirectConnection,
                Q_ARG(QImage, image)
            );
        },
        Qt::QueuedConnection
    );
}

void VideoRenderer::render(std::shared_ptr<QImage> image)
{
    if (!image)
        return;

    metric_fallback_presents.fetch_add(1);
    emit present(*image);
}

bool VideoRenderer::renderGpu(std::shared_ptr<openshot::GpuFrameSurface> surface)
{
    auto *settings = openshot::Settings::Instance();
    if (!settings->ENABLE_D3D11_ZERO_COPY || !settings->ENABLE_D3D11_DIRECT_PRESENT)
        return false;
    const uintptr_t window_address = target_window.load();
    if (!surface || !window_address || !d3d11_presenter)
        return false;

    const auto started = std::chrono::steady_clock::now();
    const bool presented = d3d11_presenter->Present(surface, window_address);
    metric_direct_present_nanoseconds.fetch_add(static_cast<uint64_t>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now() - started
        ).count()
    ));
    if (presented)
        metric_direct_presents.fetch_add(1);
    else
        metric_present_failures.fetch_add(1);
    return presented;
}

std::string VideoRenderer::PerformanceMetricsJson() const
{
    Json::Value metrics;
    metrics["direct_presents"] = static_cast<Json::UInt64>(metric_direct_presents.load());
    metrics["fallback_presents"] = static_cast<Json::UInt64>(metric_fallback_presents.load());
    metrics["present_failures"] = static_cast<Json::UInt64>(metric_present_failures.load());
    metrics["direct_present_ms"] = metric_direct_present_nanoseconds.load() / 1000000.0;
    metrics["target_window"] = static_cast<Json::UInt64>(target_window.load());
    return metrics.toStyledString();
}

void VideoRenderer::ResetPerformanceMetrics()
{
    metric_direct_presents.store(0);
    metric_fallback_presents.store(0);
    metric_present_failures.store(0);
    metric_direct_present_nanoseconds.store(0);
}

void VideoRenderer::CaptureNextFrame(const std::string& path)
{
    if (d3d11_presenter)
        d3d11_presenter->CaptureNextFrame(path);
}
