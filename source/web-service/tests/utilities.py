from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import uuid


@dataclass(frozen=True)
class AnnotationOptions:
    """
    Optional parameters to enrich the annotation.
    - annotation_id: Provide a stable ID; otherwise a URN UUID is generated.
    - created: ISO 8601 timestamp; otherwise UTC 'now' is used.
    - motivation: A Web Annotation motivation, e.g., "commenting", "tagging", "linking".
    - creator: A dict identifying the agent (e.g., {"id": "...", "type": "Person", "name": "..."})
    - language: RFC 5646 language tag for textual body, e.g., "en", "en-GB" (only used with body_string).
    - format_: MIME type of textual body, defaults to "text/plain" (only used with body_string).
    """

    annotation_id: Optional[str] = None
    created: Optional[str] = None
    motivation: Optional[str] = None
    creator: Optional[Dict[str, Any]] = None
    language: Optional[str] = None
    format_: Optional[str] = None


def create_web_annotation(
    *,
    target: str,
    body_string: Optional[str] = None,
    body_uri: Optional[str] = None,
    body_generator: Optional[str] = None,
    target_generator: Optional[str] = None,
    annotation_id_base: Optional[str] = "",
    options: Optional[AnnotationOptions] = None,
) -> Dict[str, Any]:
    """
    Parameters:
        target: str
            The IRI of the target resource (becomes {"id": target}).
        body_string: Optional[str]
            The literal textual content for the annotation body.
        body_uri: Optional[str]
            The IRI of the body resource; used as {"id": body_uri}.
        body_generator/target_generator: Optional[str]
            If present, will add the verbatim value as a 'generator' property value to the respective object.
            body_generator has no effect if it is a body_string.
        options: Optional[AnnotationOptions]
            Optional enrichment parameters (id, created, motivation, creator, language, format_).

    Returns:
        dict: A JSON-LD-compliant Web Annotation object.

    Raises:
        ValueError: If neither or both of `body_string` and `body_uri` are provided,
                    or if `target` is missing/empty.
    """
    if not isinstance(target, str) or not target.strip():
        raise ValueError("`target` must be a non-empty string (IRI).")

    has_string = body_string is not None and body_string != ""
    has_uri = body_uri is not None and body_uri != ""
    if has_string == has_uri:  # either both True or both False
        raise ValueError(
            "Provide exactly one of `body_string` or `body_uri` (but not both)."
        )

    opts = options or AnnotationOptions()

    anno_id = opts.annotation_id or f"{annotation_id_base}{uuid.uuid4()}"
    created_iso = opts.created or datetime.now(timezone.utc).isoformat()

    annotation: Dict[str, Any] = {
        "@context": "https://www.w3.org/ns/anno.jsonld",
        "id": anno_id,
        "type": "Annotation",
        "created": created_iso,
        "target": {"id": target},
    }

    if target_generator:
        annotation["target"]["generator"] = target_generator

    # motivation is optional per the model
    if opts.motivation:
        annotation["motivation"] = opts.motivation

    # creator is optional; should itself be a JSON-LD Agent-like structure but tbh
    # we tend to just use {'name': '....'}.
    if opts.creator:
        annotation["creator"] = opts.creator

    # Build body
    if has_string:
        body_obj: Dict[str, Any] = {
            "type": "TextualBody",
            "value": body_string,
            "format": opts.format_ or "text/plain",
        }
        if opts.language:
            body_obj["language"] = opts.language
        annotation["body"] = body_obj
    else:
        # body as an IRI reference
        annotation["body"] = {"id": body_uri}
        if body_generator:
            annotation["body"]["generator"] = body_generator

    return annotation


FAKE_MOVIE_ANNOTATIONS = (
    [
        {
            "target": "https://www.imdb.com/title/tt0000001/",
            "body_string": "Critics highlight confident direction, memorable performances, and resonant themes; minor pacing quibbles appear, yet consensus finds the film compelling and emotionally rewarding.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000002/",
            "body_string": "Audiences praise stunning cinematography and layered storytelling; a few note uneven tone, but overall sentiment applauds ambition, craft, and lasting impact.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000003/",
            "body_string": "Reviewers celebrate tight writing, textured characters, and assured pacing; occasional predictability is mentioned without dampening strong enthusiasm.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000004/",
            "body_string": "Widely admired for atmosphere and mood, with standout acting and a haunting score; some find the ending abrupt, though most consider it striking and memorable.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000005/",
            "body_string": "Praised for bold vision and emotional depth, blending intimate drama with spectacle; minor critiques target exposition, yet reception remains highly positive.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000006/",
            "body_string": "Critics commend elegant structure and compelling arcs; dialogue shines, while a few lament familiarity; overall, reviews favor craftsmanship and heart.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000007/",
            "body_string": "Viewers applaud relentless momentum, sharp editing, and charismatic leads; detractors cite thin subplots, but general consensus deems it exhilarating.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000008/",
            "body_string": "Acclaimed for nuanced performances and careful world-building; some pacing lulls surface, yet reviews regard it as immersive and thoughtful.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000009/",
            "body_string": "Celebrated for inventive staging, thematic richness, and confident tone; occasional tonal whiplash is forgiven amid overall admiration.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000010/",
            "body_string": "Reviewers note graceful character work, lyrical visuals, and affecting score; a handful call it slow, though many cherish its quiet power.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000011/",
            "body_string": "Praise centers on fearless performances and taut direction; some critique convenience in plotting; consensus appreciates intensity and emotional clarity.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000012/",
            "body_string": "Critics laud precise storytelling, witty dialogue, and thematic weight; minor complaints about length arise, but reception stays enthusiastic.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000013/",
            "body_string": "Audiences admire craftsmanship, textured sound design, and striking images; a few question plausibility, yet sentiment remains strongly favorable.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000014/",
            "body_string": "Applauded for confident storytelling and emotional resonance; some uneven pacing is noted, but most consider it gripping and heartfelt.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000015/",
            "body_string": "Widely praised for atmosphere, meticulous details, and committed acting; minor narrative detours divide critics, though admiration dominates.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000016/",
            "body_string": "Reviews highlight elegant visuals, sustained tension, and moral complexity; a few find character motivations opaque, yet acclaim is strong.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000017/",
            "body_string": "Critics celebrate brisk pacing, sly humor, and polished set pieces; some call it derivative, but overall reaction is delighted.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000018/",
            "body_string": "Warmly received for compassion, thematic depth, and standout lead; sporadic melodrama comments appear, though consensus appreciates its sincerity.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000019/",
            "body_string": "Viewers praise intricate plotting, visual flair, and emotional stakes; a few mention convoluted twists, yet reviews remain largely positive.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000020/",
            "body_string": "Noted for immersive world-building, measured performances, and assured tone; minor repetitiveness is overlooked amid broad approval.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000021/",
            "body_string": "Critics admire the film’s wit, confident rhythm, and resonant themes; some wish for deeper supporting arcs; overall reception is enthusiastic.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000022/",
            "body_string": "Lauded for inventive structure and evocative imagery; a divisive finale sparks discussion, yet praise outweighs reservations.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000023/",
            "body_string": "Reviewers emphasize emotional honesty, grounded performances, and subtle humor; a handful consider it slight, but many find it touching.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000024/",
            "body_string": "Commended for kinetic energy, memorable antagonist, and confident direction; some criticize thin characterization, though excitement prevails.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000025/",
            "body_string": "Audiences appreciate meticulous craft, layered subtext, and bold choices; occasional confusion surfaces, yet admiration is strong.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000026/",
            "body_string": "Praised for balance of spectacle and intimacy, with a magnetic lead; a few pacing dips are noted, but overall impressions are glowing.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000027/",
            "body_string": "Critics hail rich atmosphere, striking color, and confident symbolism; detractors cite opacity, while many celebrate its artistry.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000028/",
            "body_string": "Reviewers admire taut suspense, economical storytelling, and satisfying payoff; some desire deeper backstories, yet consensus is favorable.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000029/",
            "body_string": "Applauded for thought-provoking themes, memorable score, and elegant pacing; minor quibbles target predictability, but acclaim dominates.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000030/",
            "body_string": "Warm reception for charming script, heartfelt moments, and lively ensemble; a few jokes miss, yet the film delights.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000031/",
            "body_string": "Celebrated for audacious vision, commanding performances, and resonant allegory; some uneven tone is forgiven amid admiration.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000032/",
            "body_string": "Viewers cite tight editing, compelling stakes, and confident world-building; minor exposition clunkiness appears, but energy wins over.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000033/",
            "body_string": "Critics commend intricate character dynamics and lyrical craftsmanship; a handful find it slow, yet many call it mesmerizing.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000034/",
            "body_string": "Praised for blend of humor and pathos, anchored by humane performances; some formula elements appear, though warmth prevails.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000035/",
            "body_string": "Admired for meticulous production design, tactile soundscape, and confident suspense; a few label it chilly, but reviews are positive.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000036/",
            "body_string": "Reviewers applaud narrative economy, striking images, and a compelling arc; occasional clichés are outweighed by craft.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000037/",
            "body_string": "Strong notices for heartfelt storytelling, credible relationships, and grounded direction; minor sentimentality is noted, yet affection is widespread.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000038/",
            "body_string": "Critics praise muscular pacing, inventive set pieces, and charismatic chemistry; thin villains are mentioned, but thrills satisfy.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000039/",
            "body_string": "Admired for intelligence and restraint, with an unforgettable climax; a few call it austere, yet esteem is high.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000040/",
            "body_string": "Warm acclaim for textured ensemble, nuanced script, and evocative music; some find the structure meandering, though impact lingers.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000041/",
            "body_string": "Viewers celebrate emotional heft, deft humor, and quietly dazzling visuals; minor third-act wobble aside, reception is glowing.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000042/",
            "body_string": "Critics enjoy brisk plotting, clever reversals, and satisfying catharsis; a few nitpick coincidences, yet praise dominates.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000043/",
            "body_string": "Lauded for atmospheric tension, confident minimalism, and an empathetic core; some wish for more answers, but admiration persists.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000044/",
            "body_string": "Reviews applaud humane tone, generous humor, and heartfelt performances; slight pacing issues are overshadowed by charm.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000045/",
            "body_string": "Acclaimed for thematic ambition, elegant framing, and commanding lead work; occasional opacity divides viewers, yet esteem is strong.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000046/",
            "body_string": "Audiences admire propulsive action, clear geography, and practical effects; character depth is modest, but excitement never flags.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000047/",
            "body_string": "Critics note poetic imagery, subtle performances, and affecting intimacy; a deliberately slow tempo rewards patient viewers.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000048/",
            "body_string": "Praise centers on confident tone, sharp humor, and generous spirit; a few gags overstay, though goodwill remains high.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000049/",
            "body_string": "Reviewers celebrate craftsmanship, emotional stakes, and a resonant finale; small logic gaps are easily forgiven.",
        },
        {
            "target": "https://www.imdb.com/title/tt0000050/",
            "body_string": "Widely admired for bold choices, muscular direction, and layered subtext; some unevenness aside, impact is considerable.",
        },
    ]
    + [
        {
            "target": f"https://www.imdb.com/title/tt{str(5000000 + i).zfill(7)}/",
            "body_string": (
                "Reviewers praise confident direction, engaging performances, and strong craft; "
                "occasional pacing concerns arise, but overall sentiment remains positive and appreciative."
            ),
        }
        for i in range(51, 201)
    ]
    + [
        {
            "target": f"https://www.imdb.com/title/tt{str(6000000 + i).zfill(7)}/",
            "body_string": (
                "Critics highlight striking visuals, thematic depth, and assured storytelling; "
                "some note familiar beats, yet consensus considers it compelling and rewarding."
            ),
        }
        for i in range(201, 251)
    ]
    + [
        {
            "target": f"https://www.imdb.com/title/tt{str(7000000 + i).zfill(7)}/",
            "body_string": (
                "Audiences commend immersive atmosphere, resonant score, and memorable moments; "
                "minor quibbles exist, but reviews trend warmly overall."
            ),
        }
        for i in range(251, 301)
    ]
)
