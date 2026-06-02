/*
 * Persist the learner model to a single JSON file in the app's private dir.
 *
 * The on-disk shape mirrors konjugaton's `VocabState.to_dict` (version, scores,
 * abilities) so a state file is portable between this app and the CLI. No Room,
 * no SQLite — one file, atomically replaced. Simplicity wins.
 */
package com.konjugaton.hc.data

import com.konjugaton.hc.domain.KnowledgeType
import com.konjugaton.hc.domain.ScoreCell
import com.konjugaton.hc.domain.VocabState
import java.io.File
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

@Serializable
private data class CellDto(
    val attempts: Int,
    val correct: Int,
    val ewma: Double,
    val last_seen: String? = null,
)

@Serializable
private data class StateDto(
    val version: Int = 1,
    val scores: Map<String, Map<String, CellDto>> = emptyMap(),
    val abilities: Map<String, Double> = emptyMap(),
)

private val JSON = Json { ignoreUnknownKeys = true; prettyPrint = false }

/** Reads/writes [VocabState] as a JSON file. */
class StateStore(private val file: File) {

    fun load(): VocabState {
        if (!file.exists()) return VocabState()
        return try {
            val dto = JSON.decodeFromString<StateDto>(file.readText())
            VocabState(
                scores = dto.scores.mapValues { (_, kmap) ->
                    kmap.entries.associate { (k, c) ->
                        KnowledgeType.fromValue(k) to ScoreCell(
                            attempts = c.attempts,
                            correct = c.correct,
                            ewma = c.ewma,
                            lastSeen = c.last_seen,
                        )
                    }.toMutableMap()
                }.toMutableMap(),
                abilities = dto.abilities.toMutableMap(),
            )
        } catch (_: Exception) {
            // Corrupt state file is recoverable: start fresh rather than crash.
            VocabState()
        }
    }

    fun save(state: VocabState) {
        val dto = StateDto(
            version = 1,
            scores = state.scores.mapValues { (_, kmap) ->
                kmap.entries.associate { (k, cell) ->
                    k.value to CellDto(
                        attempts = cell.attempts,
                        correct = cell.correct,
                        ewma = (Math.round(cell.ewma * 1_000_000.0) / 1_000_000.0),
                        last_seen = cell.lastSeen,
                    )
                }
            },
            abilities = state.abilities,
        )
        val tmp = File(file.parentFile, "${file.name}.tmp")
        tmp.writeText(JSON.encodeToString(dto))
        tmp.renameTo(file)
    }
}
