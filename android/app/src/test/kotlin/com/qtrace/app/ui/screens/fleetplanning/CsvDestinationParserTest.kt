package com.qtrace.app.ui.screens.fleetplanning

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Test

class CsvDestinationParserTest {

    @Test
    fun `parses a row with coordinates directly`() {
        val csv = "name,demand,time_window_start,time_window_end,service_time_minutes,latitude,longitude\n" +
            "T Nagar,20,09:00,11:00,10,13.0418,80.2341"

        val result = CsvDestinationParser.parse(csv)

        assertEquals(1, result.size)
        val destination = result.first()
        assertEquals("T Nagar", destination.name)
        assertEquals("20", destination.demand)
        assertEquals("09:00", destination.timeWindowStart)
        assertEquals("11:00", destination.timeWindowEnd)
        assertEquals("10", destination.serviceTimeMinutes)
        assertEquals(13.0418, destination.coordinate?.latitude)
        assertEquals(80.2341, destination.coordinate?.longitude)
        assertNull(destination.address)
    }

    @Test
    fun `falls back to name as address when coordinates and address are absent`() {
        val csv = "name,demand\nT Nagar,20"

        val result = CsvDestinationParser.parse(csv)

        assertEquals("T Nagar", result.first().address)
        assertNull(result.first().coordinate)
    }

    @Test
    fun `uses explicit address column when given, over the name`() {
        val csv = "name,address\nWarehouse A,123 Anna Salai Chennai"

        val result = CsvDestinationParser.parse(csv)

        assertEquals("123 Anna Salai Chennai", result.first().address)
    }

    @Test
    fun `header columns are matched case-insensitively and in any order`() {
        val csv = "DEMAND,NAME\n15,Guindy"

        val result = CsvDestinationParser.parse(csv)

        assertEquals("Guindy", result.first().name)
        assertEquals("15", result.first().demand)
    }

    @Test
    fun `missing required name column throws`() {
        val csv = "demand,address\n20,Somewhere"

        assertThrows(CsvParseException::class.java) { CsvDestinationParser.parse(csv) }
    }

    @Test
    fun `blank name cell throws with a helpful row number`() {
        val csv = "name,demand\n,20"

        val error = assertThrows(CsvParseException::class.java) { CsvDestinationParser.parse(csv) }
        assertEquals("Row 2: missing a name.", error.message)
    }

    @Test
    fun `empty file throws`() {
        assertThrows(CsvParseException::class.java) { CsvDestinationParser.parse("") }
    }

    @Test
    fun `defaults are applied for omitted optional columns`() {
        val csv = "name\nDepot Stop"

        val destination = CsvDestinationParser.parse(csv).first()

        assertEquals("0", destination.demand)
        assertEquals("", destination.timeWindowStart)
        assertEquals("", destination.timeWindowEnd)
        assertEquals("0", destination.serviceTimeMinutes)
    }
}
