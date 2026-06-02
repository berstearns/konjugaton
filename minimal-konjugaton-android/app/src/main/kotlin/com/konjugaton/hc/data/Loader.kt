/*
 * Load and validate the bundled taxonomy JSON, returning a pure-domain Catalog.
 *
 * Port of konjugaton's `data/loader.py` + `data/models.py`: @Serializable DTOs
 * are the I/O boundary (they mirror the JSON), then they're mapped to
 * framework-free domain objects — the domain never sees a serialization type.
 *
 * `parse(...)` takes the three JSON strings, so it is unit-testable on the plain
 * JVM. Reading the bytes from Android assets is the caller's job (AppState).
 */
package com.konjugaton.hc.data

import com.konjugaton.hc.domain.Catalog
import com.konjugaton.hc.domain.ConjugationData
import com.konjugaton.hc.domain.EndingTables
import com.konjugaton.hc.domain.PerfectiveForms
import com.konjugaton.hc.domain.SemanticContext
import com.konjugaton.hc.domain.Transitivity
import com.konjugaton.hc.domain.Verb
import com.konjugaton.hc.domain.VerbClass
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

private val JSON = Json { ignoreUnknownKeys = true }

// --- DTOs (mirror the asset JSON exactly) ---------------------------------

@Serializable
private data class PerfectiveDto(
    val devanagari: Map<String, String>,
    val romanized: Map<String, String>,
)

@Serializable
private data class ConjugationDto(
    val root: String? = null,
    @SerialName("root_roman") val rootRoman: String? = null,
    @SerialName("future_oblique") val futureOblique: String? = null,
    @SerialName("future_oblique_roman") val futureObliqueRoman: String? = null,
    @SerialName("imperative_aap") val imperativeAap: String? = null,
    @SerialName("imperative_aap_roman") val imperativeAapRoman: String? = null,
    val perfective: PerfectiveDto? = null,
)

@Serializable
private data class VerbDto(
    val lemma: String,
    @SerialName("lemma_roman") val lemmaRoman: String,
    @SerialName("verb_class") val verbClass: String,
    val transitivity: String,
    val translation: String,
    @SerialName("frequency_rank") val frequencyRank: Int,
    val family: String? = null,
    @SerialName("semantic_tags") val semanticTags: List<String> = emptyList(),
    val conjugation: ConjugationDto? = null,
)

@Serializable
private data class VerbsFileDto(val verbs: List<VerbDto>)

@Serializable
private data class ScriptTableDto(
    val devanagari: Map<String, String>,
    val romanized: Map<String, String>,
)

@Serializable
private data class EndingsDto(
    val imperfective: ScriptTableDto,
    val perfective: ScriptTableDto,
    @SerialName("perfective_glide") val perfectiveGlide: ScriptTableDto,
    val future: ScriptTableDto,
    @SerialName("future_tail") val futureTail: ScriptTableDto,
    val subjunctive: ScriptTableDto,
    val imperative: ScriptTableDto,
    @SerialName("hona_present") val honaPresent: ScriptTableDto,
    @SerialName("hona_past") val honaPast: ScriptTableDto,
    val progressive: ScriptTableDto,
)

@Serializable
private data class ContextDto(
    val id: String,
    @SerialName("label_hi") val labelHi: String,
    @SerialName("label_en") val labelEn: String,
    val templates: List<String>,
    @SerialName("templates_roman") val templatesRoman: List<String>,
    val affinity: List<String> = emptyList(),
)

@Serializable
private data class ContextsFileDto(val contexts: List<ContextDto>)

// --- mapping DTO -> domain -------------------------------------------------

private fun VerbDto.toDomain(): Verb {
    val conj = conjugation
    val perfective = conj?.perfective?.let { PerfectiveForms(it.devanagari, it.romanized) }
    return Verb(
        lemma = lemma,
        lemmaRoman = lemmaRoman,
        verbClass = VerbClass.fromValue(verbClass),
        transitivity = Transitivity.fromValue(transitivity),
        translation = translation,
        frequencyRank = frequencyRank,
        conjugation = ConjugationData(
            root = conj?.root,
            rootRoman = conj?.rootRoman,
            perfective = perfective,
            futureOblique = conj?.futureOblique,
            futureObliqueRoman = conj?.futureObliqueRoman,
            imperativeAap = conj?.imperativeAap,
            imperativeAapRoman = conj?.imperativeAapRoman,
        ),
        family = family,
        semanticTags = semanticTags,
    )
}

object CatalogLoader {
    /** Parse the three taxonomy JSON documents into a single [Catalog]. */
    fun parse(verbsJson: String, endingsJson: String, contextsJson: String): Catalog {
        val verbsFile = JSON.decodeFromString<VerbsFileDto>(verbsJson)
        val e = JSON.decodeFromString<EndingsDto>(endingsJson)
        val contextsFile = JSON.decodeFromString<ContextsFileDto>(contextsJson)

        val verbs = verbsFile.verbs.associate { it.lemma to it.toDomain() }

        val dev = mapOf(
            "imperfective" to e.imperfective.devanagari,
            "perfective" to e.perfective.devanagari,
            "perfective_glide" to e.perfectiveGlide.devanagari,
            "future" to e.future.devanagari,
            "future_tail" to e.futureTail.devanagari,
            "subjunctive" to e.subjunctive.devanagari,
            "imperative" to e.imperative.devanagari,
            "hona_present" to e.honaPresent.devanagari,
            "hona_past" to e.honaPast.devanagari,
            "progressive" to e.progressive.devanagari,
        )
        val rom = mapOf(
            "imperfective" to e.imperfective.romanized,
            "perfective" to e.perfective.romanized,
            "perfective_glide" to e.perfectiveGlide.romanized,
            "future" to e.future.romanized,
            "future_tail" to e.futureTail.romanized,
            "subjunctive" to e.subjunctive.romanized,
            "imperative" to e.imperative.romanized,
            "hona_present" to e.honaPresent.romanized,
            "hona_past" to e.honaPast.romanized,
            "progressive" to e.progressive.romanized,
        )
        val endingTables = EndingTables(dev, rom)

        val contexts = contextsFile.contexts.associate {
            it.id to SemanticContext(
                id = it.id,
                labelHi = it.labelHi,
                labelEn = it.labelEn,
                templates = it.templates,
                templatesRoman = it.templatesRoman,
                affinity = it.affinity,
            )
        }

        return Catalog(verbs = verbs, endings = endingTables, contexts = contexts)
    }
}
