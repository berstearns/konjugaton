/*
 * Load and validate the bundled taxonomy JSON, returning a pure-domain Catalog.
 *
 * Port of konjugaton's `data/loader.py` + `data/models.py` (German): @Serializable
 * DTOs are the I/O boundary (they mirror the JSON), then they're mapped to
 * framework-free domain objects — the domain never sees a serialization type.
 *
 * `parse(...)` takes the three JSON strings, so it is unit-testable on the plain
 * JVM. Reading the bytes from Android assets is the caller's job (AppState).
 */
package com.konjugaton.hc.data

import com.konjugaton.hc.domain.Auxiliary
import com.konjugaton.hc.domain.Catalog
import com.konjugaton.hc.domain.ConjugationData
import com.konjugaton.hc.domain.EndingTables
import com.konjugaton.hc.domain.SemanticContext
import com.konjugaton.hc.domain.Verb
import com.konjugaton.hc.domain.VerbClass
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

private val JSON = Json { ignoreUnknownKeys = true }

// --- DTOs (mirror the asset JSON exactly) ---------------------------------

@Serializable
private data class ConjugationDto(
    @SerialName("praesens_stem_23") val praesensStem23: String? = null,
    @SerialName("praeteritum_stem") val praeteritumStem: String? = null,
    val partizip2: String? = null,
    @SerialName("konjunktiv2_stem") val konjunktiv2Stem: String? = null,
    val irregular: Map<String, Map<String, String>> = emptyMap(),
)

@Serializable
private data class VerbDto(
    val lemma: String,
    val translation: String,
    @SerialName("verb_class") val verbClass: String,
    val auxiliary: String,
    val transitive: Boolean,
    @SerialName("frequency_rank") val frequencyRank: Int,
    @SerialName("separable_prefix") val separablePrefix: String? = null,
    val family: String? = null,
    @SerialName("semantic_tags") val semanticTags: List<String> = emptyList(),
    val conjugation: ConjugationDto? = null,
)

@Serializable
private data class VerbsFileDto(val verbs: List<VerbDto>)

@Serializable
private data class ContextDto(
    val id: String,
    @SerialName("label_de") val labelDe: String,
    @SerialName("label_en") val labelEn: String,
    val templates: List<String>,
    val affinity: List<String> = emptyList(),
)

@Serializable
private data class ContextsFileDto(val contexts: List<ContextDto>)

// --- mapping DTO -> domain -------------------------------------------------

private fun VerbDto.toDomain(): Verb {
    val conj = conjugation
    return Verb(
        lemma = lemma,
        translation = translation,
        verbClass = VerbClass.fromValue(verbClass),
        auxiliary = Auxiliary.fromValue(auxiliary),
        transitive = transitive,
        frequencyRank = frequencyRank,
        conjugation = ConjugationData(
            praesensStem23 = conj?.praesensStem23,
            praeteritumStem = conj?.praeteritumStem,
            partizip2 = conj?.partizip2,
            konjunktiv2Stem = conj?.konjunktiv2Stem,
            irregular = conj?.irregular ?: emptyMap(),
        ),
        separablePrefix = separablePrefix,
        family = family,
        semanticTags = semanticTags,
    )
}

object CatalogLoader {
    /** Parse the three taxonomy JSON documents into a single [Catalog]. */
    fun parse(verbsJson: String, endingsJson: String, contextsJson: String): Catalog {
        val verbsFile = JSON.decodeFromString<VerbsFileDto>(verbsJson)
        val endingsRaw = JSON.decodeFromString<Map<String, Map<String, String>>>(endingsJson)
        val contextsFile = JSON.decodeFromString<ContextsFileDto>(contextsJson)

        val verbs = verbsFile.verbs.associate { it.lemma to it.toDomain() }
        val endingTables = EndingTables(endingsRaw)
        val contexts = contextsFile.contexts.associate {
            it.id to SemanticContext(
                id = it.id,
                labelDe = it.labelDe,
                labelEn = it.labelEn,
                templates = it.templates,
                affinity = it.affinity,
            )
        }

        return Catalog(verbs = verbs, endings = endingTables, contexts = contexts)
    }
}
