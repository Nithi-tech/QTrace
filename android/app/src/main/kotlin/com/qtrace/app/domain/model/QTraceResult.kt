package com.qtrace.app.domain.model

/** Repository-layer result: success with data, or a structured, user-mappable failure. */
sealed class QTraceResult<out T> {
    data class Success<T>(val data: T) : QTraceResult<T>()
    data class Failure(val error: QTraceError) : QTraceResult<Nothing>()
}
