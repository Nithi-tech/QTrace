package com.qtrace.app.domain.model

import org.junit.Assert.assertThrows
import org.junit.Test

class CoordinateTest {

    @Test
    fun `accepts boundary values`() {
        Coordinate(latitude = 90.0, longitude = 180.0)
        Coordinate(latitude = -90.0, longitude = -180.0)
    }

    @Test
    fun `rejects latitude above 90`() {
        assertThrows(IllegalArgumentException::class.java) {
            Coordinate(latitude = 90.1, longitude = 0.0)
        }
    }

    @Test
    fun `rejects latitude below negative 90`() {
        assertThrows(IllegalArgumentException::class.java) {
            Coordinate(latitude = -90.1, longitude = 0.0)
        }
    }

    @Test
    fun `rejects longitude above 180`() {
        assertThrows(IllegalArgumentException::class.java) {
            Coordinate(latitude = 0.0, longitude = 180.1)
        }
    }

    @Test
    fun `rejects longitude below negative 180`() {
        assertThrows(IllegalArgumentException::class.java) {
            Coordinate(latitude = 0.0, longitude = -180.1)
        }
    }
}
