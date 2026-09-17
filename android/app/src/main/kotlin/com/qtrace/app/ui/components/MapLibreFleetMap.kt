package com.qtrace.app.ui.components

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color as AndroidColor
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.qtrace.app.R
import com.qtrace.app.domain.model.Coordinate
import com.qtrace.app.domain.model.VehicleRouteResult
import org.maplibre.android.annotations.IconFactory
import org.maplibre.android.annotations.MarkerOptions
import org.maplibre.android.camera.CameraUpdateFactory
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.geometry.LatLngBounds
import org.maplibre.android.maps.MapView
import org.maplibre.android.maps.Style
import org.maplibre.android.style.layers.LineLayer
import org.maplibre.android.style.layers.Property
import org.maplibre.android.style.layers.PropertyFactory
import org.maplibre.android.style.sources.GeoJsonSource
import org.maplibre.geojson.Feature
import org.maplibre.geojson.LineString
import org.maplibre.geojson.Point

private const val MAX_ROUTE_LAYERS = 32
private const val CAMERA_PADDING_PX = 120
private const val MARKER_RADIUS_PX = 17f
private const val DEPOT_HALF_SIZE_PX = 21f
private const val ICON_PADDING_PX = 14
private const val MARKER_DIAMETER_PX = (MARKER_RADIUS_PX.toInt() * 2) + ICON_PADDING_PX * 2
private const val DEPOT_DIAMETER_PX = (DEPOT_HALF_SIZE_PX.toInt() * 2) + ICON_PADDING_PX * 2
private const val UNASSIGNED_STOP_COLOR = "#C4271B"
private const val UNVISITED_STOP_COLOR = "#78909C"
private const val DEPOT_COLOR = "#1A2027"
private const val SHADOW_COLOR = "#33000000"

/** A fixed, colorblind-friendlier palette, cycled by vehicle index so each route on the map
 * (and its legend entry) is visually distinct regardless of how many vehicles are used. */
val FLEET_ROUTE_COLORS = listOf(
    "#1B5E44", "#B5560B", "#1F5FA8", "#8E2C8F", "#C4271B",
    "#0F766E", "#7C3AED", "#B45309", "#0369A1", "#4D7C0F",
)

fun colorForVehicle(index: Int): String = FLEET_ROUTE_COLORS[index % FLEET_ROUTE_COLORS.size]

/** One destination pin to render: which vehicle (if any) serves it and its visit order within
 * that vehicle's route, so the marker itself - not just the route line - shows which vehicle a
 * stop belongs to. [vehicleIndex] and [visitOrder] are null before routes exist (e.g. the Review
 * step's preview map) or for a destination the optimizer couldn't assign. */
data class FleetStopMarker(
    val coordinate: Coordinate,
    val vehicleIndex: Int? = null,
    val visitOrder: Int? = null,
    val isUnassigned: Boolean = false,
)

/**
 * Multi-vehicle map: a distinct dark depot badge, one softly-shadowed circular pin per
 * destination colored to match the vehicle that serves it (with its visit-order number so
 * overlapping stops stay distinguishable even when routes cross), and one bold, colored route
 * line per vehicle with a soft dark halo beneath it so crossing/overlapping routes near the depot
 * stay legible instead of merging into a smear. Rendered over a plain, muted basemap (see
 * BuildConfig.MAP_STYLE_URL) so these colors are the visually dominant thing on screen, not
 * competing with a busy map underneath. Provider-specific rendering stays entirely inside this
 * component, matching MapLibreRouteMap's separation (CLAUDE.md #7/#13/#17).
 */
@Composable
fun MapLibreFleetMap(
    styleUrl: String,
    depot: Coordinate?,
    destinationMarkers: List<FleetStopMarker>,
    vehicleRoutes: List<VehicleRouteResult>,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val mapView = remember { MapView(context) }

    DisposableEffect(lifecycleOwner, mapView) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_CREATE -> mapView.onCreate(null)
                Lifecycle.Event.ON_START -> mapView.onStart()
                Lifecycle.Event.ON_RESUME -> mapView.onResume()
                Lifecycle.Event.ON_PAUSE -> mapView.onPause()
                Lifecycle.Event.ON_STOP -> mapView.onStop()
                Lifecycle.Event.ON_DESTROY -> mapView.onDestroy()
                else -> Unit
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    val contentDescriptionLabel = stringResource(R.string.content_description_fleet_map)

    AndroidView(
        factory = { mapView.apply { contentDescription = contentDescriptionLabel } },
        modifier = modifier,
        update = { view ->
            view.getMapAsync { maplibreMap ->
                maplibreMap.setStyle(Style.Builder().fromUri(styleUrl)) { style ->
                    renderRoutes(style, vehicleRoutes)
                    renderMarkers(context, maplibreMap, depot, destinationMarkers)
                    fitCamera(maplibreMap, depot, destinationMarkers, vehicleRoutes)
                }
            }
        },
    )
}

private fun renderRoutes(style: Style, vehicleRoutes: List<VehicleRouteResult>) {
    for (i in 0 until MAX_ROUTE_LAYERS) {
        style.getLayer("qtrace-fleet-route-layer-$i")?.let { style.removeLayer(it) }
        style.getLayer("qtrace-fleet-route-casing-$i")?.let { style.removeLayer(it) }
        style.getSource("qtrace-fleet-route-source-$i")?.let { style.removeSource(it) }
    }

    vehicleRoutes.forEachIndexed { index, route ->
        if (route.geometry.size < 2) return@forEachIndexed
        val points = route.geometry.map { Point.fromLngLat(it.longitude, it.latitude) }
        val source = GeoJsonSource(
            "qtrace-fleet-route-source-$index",
            Feature.fromGeometry(LineString.fromLngLats(points)),
        )
        style.addSource(source)
        // A soft, semi-transparent dark halo beneath the colored line reads as a drop shadow on
        // the plain basemap - it keeps overlapping/crossing routes near the depot separable
        // without the harsh look (or light-basemap invisibility) of a solid white outline.
        style.addLayer(
            LineLayer("qtrace-fleet-route-casing-$index", "qtrace-fleet-route-source-$index").withProperties(
                PropertyFactory.lineColor(AndroidColor.parseColor(SHADOW_COLOR)),
                PropertyFactory.lineWidth(9.5f),
                PropertyFactory.lineCap(Property.LINE_CAP_ROUND),
                PropertyFactory.lineJoin(Property.LINE_JOIN_ROUND),
            ),
        )
        style.addLayer(
            LineLayer("qtrace-fleet-route-layer-$index", "qtrace-fleet-route-source-$index").withProperties(
                PropertyFactory.lineColor(AndroidColor.parseColor(colorForVehicle(index))),
                PropertyFactory.lineWidth(5.5f),
                PropertyFactory.lineCap(Property.LINE_CAP_ROUND),
                PropertyFactory.lineJoin(Property.LINE_JOIN_ROUND),
            ),
        )
    }
}

private fun renderMarkers(
    context: Context,
    maplibreMap: org.maplibre.android.maps.MapLibreMap,
    depot: Coordinate?,
    destinationMarkers: List<FleetStopMarker>,
) {
    maplibreMap.markers.toList().forEach { maplibreMap.removeMarker(it) }

    depot?.let {
        maplibreMap.addMarker(
            MarkerOptions()
                .position(LatLng(it.latitude, it.longitude))
                .icon(depotIcon(context)),
        )
    }
    destinationMarkers.forEach { stop ->
        val color = when {
            stop.isUnassigned -> UNASSIGNED_STOP_COLOR
            stop.vehicleIndex != null -> colorForVehicle(stop.vehicleIndex)
            else -> UNVISITED_STOP_COLOR
        }
        maplibreMap.addMarker(
            MarkerOptions()
                .position(LatLng(stop.coordinate.latitude, stop.coordinate.longitude))
                .icon(circleIcon(context, color = AndroidColor.parseColor(color), label = stop.visitOrder?.toString())),
        )
    }
}

private fun fitCamera(
    maplibreMap: org.maplibre.android.maps.MapLibreMap,
    depot: Coordinate?,
    destinationMarkers: List<FleetStopMarker>,
    vehicleRoutes: List<VehicleRouteResult>,
) {
    val routePoints = vehicleRoutes.flatMap { it.geometry }
    val points = routePoints.ifEmpty { listOfNotNull(depot) + destinationMarkers.map { it.coordinate } }
    if (points.size < 2) {
        points.singleOrNull()?.let {
            maplibreMap.moveCamera(CameraUpdateFactory.newLatLngZoom(LatLng(it.latitude, it.longitude), 12.0))
        }
        return
    }

    val bounds = LatLngBounds.Builder().apply {
        points.forEach { include(LatLng(it.latitude, it.longitude)) }
    }.build()

    maplibreMap.moveCamera(CameraUpdateFactory.newLatLngBounds(bounds, CAMERA_PADDING_PX))
}

/** A colored, softly-shadowed circular pin with a white ring and, when [label] is given (a
 * stop's visit-order number), centered bold white text - so a stop's marker alone identifies both
 * its vehicle (by color) and its place in that vehicle's route (by number), without having to
 * trace the line back to the depot. The shadow (unlike a directional drop shadow) is symmetric,
 * so the marker's visual center still sits exactly on its true coordinate. */
private fun circleIcon(context: Context, color: Int, label: String? = null) =
    IconFactory.getInstance(context).fromBitmap(
        Bitmap.createBitmap(MARKER_DIAMETER_PX, MARKER_DIAMETER_PX, Bitmap.Config.ARGB_8888).apply {
            val canvas = Canvas(this)
            val center = MARKER_DIAMETER_PX / 2f

            val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                this.color = color
                setShadowLayer(6f, 0f, 2f, AndroidColor.parseColor(SHADOW_COLOR))
            }
            canvas.drawCircle(center, center, MARKER_RADIUS_PX, fillPaint)
            canvas.drawCircle(
                center,
                center,
                MARKER_RADIUS_PX,
                Paint(Paint.ANTI_ALIAS_FLAG).apply {
                    this.color = AndroidColor.WHITE
                    style = Paint.Style.STROKE
                    strokeWidth = 3.5f
                },
            )
            if (label != null) {
                drawCenteredLabel(canvas, center, center, label, MARKER_RADIUS_PX * 1.05f)
            }
        },
    )

/** The depot gets a distinct rounded-square badge (not a circle) so its SHAPE alone - not just
 * its color - sets it apart from every stop pin at a glance, even for a colorblind user or a
 * quick glance at a small map. */
private fun depotIcon(context: Context) =
    IconFactory.getInstance(context).fromBitmap(
        Bitmap.createBitmap(DEPOT_DIAMETER_PX, DEPOT_DIAMETER_PX, Bitmap.Config.ARGB_8888).apply {
            val canvas = Canvas(this)
            val center = DEPOT_DIAMETER_PX / 2f
            val half = DEPOT_HALF_SIZE_PX
            val rect = RectF(center - half, center - half, center + half, center + half)
            val corner = half * 0.55f

            val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                color = AndroidColor.parseColor(DEPOT_COLOR)
                setShadowLayer(7f, 0f, 2f, AndroidColor.parseColor(SHADOW_COLOR))
            }
            canvas.drawRoundRect(rect, corner, corner, fillPaint)
            canvas.drawRoundRect(
                rect,
                corner,
                corner,
                Paint(Paint.ANTI_ALIAS_FLAG).apply {
                    color = AndroidColor.WHITE
                    style = Paint.Style.STROKE
                    strokeWidth = 3.5f
                },
            )
            drawCenteredLabel(canvas, center, center, "D", half * 1.1f)
        },
    )

private fun drawCenteredLabel(canvas: Canvas, x: Float, y: Float, label: String, textSize: Float) {
    val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = AndroidColor.WHITE
        textAlign = Paint.Align.CENTER
        this.textSize = textSize
        typeface = Typeface.create(Typeface.DEFAULT_BOLD, Typeface.BOLD)
    }
    val textY = y - (textPaint.descent() + textPaint.ascent()) / 2f
    canvas.drawText(label, x, textY, textPaint)
}
