"""Generic text formatters.

Anything more complicated than plain text can be rendered in Markdown,
which is then fairly easy to render to other formats as needed.
"""
import re
from typing import List, Union

from dronefly.core.constants import (
    TAXON_PRIMARY_RANKS,
    TRINOMIAL_ABBR,
    RANK_LEVELS,
)
from dronefly.core.formatters.constants import WWW_BASE_URL
import inflect
from pyinaturalist import (
    ConservationStatus,
    EstablishmentMeans,
    ListedTaxon,
    Taxon,
)

MEANS_LABEL_DESC = {
    "endemic": "endemic to",
    "native": "native in",
    "introduced": "introduced to",
}

MEANS_LABEL_EMOJI = {
    "endemic": "\N{SPARKLE}",
    "native": "\N{LARGE GREEN SQUARE}",
    "introduced": "\N{UP-POINTING SMALL RED TRIANGLE}",
}

TAXON_LIST_DELIMITER = [", ", " > "]

p = inflect.engine()


def format_link(link_text: str, url: str):
    return f"[{link_text}]({url})" if url else link_text


def format_taxon_establishment_means(
    means: Union[EstablishmentMeans, ListedTaxon],
    all_means: bool = False,
    list_title: bool = False,
):
    """Format the estalishment means for a taxon for a given place.

    Parameters:
    -----------
    means: EstablishmentMeans
        The EstablishmentMeans for the taxon at the given place.
    all_means: bool
        Whether or not to include means that normally are not shown (e.g. unknown).
    list_title: bool
        Whether or not to include the list title.

    Returns:
    --------
    str
        A Markdown-formatted string containing the means, if shown, with emoji
        and link to establishment means on the web.
    """
    label = means.establishment_means
    description = MEANS_LABEL_DESC.get(label)
    if description is None:
        if not all_means:
            return None
        full_description = f"Establishment means {label} in {means.place.display_name}"
    else:
        full_description = f"{description} {means.place.display_name}"
    try:
        emoji = MEANS_LABEL_EMOJI[means.establishment_means] + "\u202f"
    except KeyError:
        emoji = ""
    url = f"{WWW_BASE_URL}/listed_taxa/{means.id}"
    if list_title and isinstance(means, ListedTaxon) and means.list.title:
        _means = f"{emoji}{full_description} {format_link(means.list.title, url)}"
    else:
        _means = f"{emoji}{format_link(full_description, url)}"
    return _means


def format_taxon_conservation_status(
    status: ConservationStatus,
    brief: bool = False,
    inflect: bool = False,
):
    """Format the conservation status for a taxon for a given place.

    Parameters:
    -----------
    status: ConservationStatus
        The ConservationStatus for the taxon at the given place.
    brief: bool
        Whether to return brief format for use in brief taxon description
        or full format that also includes the name of the authority.
    inflect: bool
        Whether to inflect first word in status and precede with indefinite
        article for use in a sentence, e.g. "an endangered", "a secure", etc.

    Returns:
    --------
    str
        A Markdown-formatted string containing the conservation status
        with link to the status on the web.
    """
    description = status.display_name

    if brief:
        linked_status = format_link(description, status.url)
        if inflect:
            # inflect statuses with single digits in them correctly
            first_word = re.sub(
                r"[0-9]",
                " {0} ".format(p.number_to_words(r"\1")),
                description,
            ).split()[0]
            article = p.a(first_word).split()[0]
            full_description = " ".join((article, linked_status))
        else:
            full_description = linked_status
    else:
        linked_status = format_link(status.authority, status.url)
        full_description = f"{description} ({linked_status})"

    return full_description


def format_taxon_names(
    taxa: List[Taxon],
    with_term=False,
    names_format="%s",
    max_len=0,
    hierarchy=False,
    lang=None,
):
    """Format names of taxa from matched records.

    Parameters
    ----------
    taxa: List[Taxon]
        A list of Taxon records to format, either as a comma-delimited list or
        in a hierarchy.
        - If hierarchy=True, these must be in highest to lowest rank order.
    with_term: bool, optional
        With non-common / non-name matching term in parentheses in place of common name.
    names_format: str, optional
        Format string for the name. Must contain exactly one %s.
    max_len: int, optional
        The maximum length of the return str, with ', and # more' appended if they
        don't all fit within this length.
    hierarchy: bool, optional
        If specified, formats a hierarchy list of scientific names with
        primary ranks bolded & starting on a new line, and delimited with
        angle-brackets instead of commas.
    lang: str, optional
        If specified, prefer the first name with its locale == lang instead of
        the preferred_common_name.


    Returns
    -------
    str
        A delimited list of formatted taxon names.
    """

    delimiter = TAXON_LIST_DELIMITER[int(hierarchy)]

    names = [
        format_taxon_name(taxon, with_term=with_term, hierarchy=hierarchy, lang=lang)
        for taxon in taxa
    ]

    def fit_names(names):
        names_fit = []
        # Account for space already used by format string (minus 2 for %s)
        available_len = max_len - (len(names_format) - 2)

        def more(count):
            return "and %d more" % count

        def formatted_len(name):
            return sum(len(item) + len(delimiter) for item in names_fit) + len(name)

        def overflow(name):
            return formatted_len(name) > available_len

        for name in names:
            if overflow(name):
                unprocessed = len(names) - len(names_fit)
                while overflow(more(unprocessed)):
                    unprocessed += 1
                    del names_fit[-1]
                names_fit.append(more(unprocessed))
                break
            else:
                names_fit.append(name)
        return names_fit

    if max_len:
        names = fit_names(names)

    return names_format % delimiter.join(names)


def format_taxon_name(
    taxon: Taxon,
    with_term=False,
    hierarchy=False,
    with_rank=True,
    with_common=True,
    lang=None,
):
    """Format taxon name.

    Parameters
    ----------
    taxon: Taxon
        The taxon to format.
    with_term: bool, optional
        When with_common=True, non-common / non-name matching term is put in
        parentheses in place of common name.
    hierarchy: bool, optional
        If specified, produces a list item suitable for inclusion in the hierarchy section
        of a taxon embed. See format_taxon_names() for details.
    with_rank: bool, optional
        If specified and hierarchy=False, includes the rank for ranks higher than species.
    with_common: bool, optional
        If specified, include common name in parentheses after scientific name.
    lang: str, optional
        If specified, prefer the first name with its locale == lang instead of
        the preferred_common_name.

    Returns
    -------
    str
        A name of the form "Rank Scientific name (Common name)" following the
        same basic format as iNaturalist taxon pages on the web, i.e.

        - drop the "Rank" keyword for species level and lower
        - italicize the name (minus any rank abbreviations; see next point) for genus
        level and lower
        - for trinomials (must be subspecies level & have exactly 3 names to qualify),
        insert the appropriate abbreviation, unitalicized, between the 2nd and 3rd
        name (e.g. "Anser anser domesticus" -> "*Anser anser* var. *domesticus*")
    """

    if with_common:
        preferred_common_name = None
        if lang and taxon.names:
            name = next(
                iter([name for name in taxon.names if name.get("locale") == lang]), None
            )
            if name:
                preferred_common_name = name.get("name")
        if not preferred_common_name:
            preferred_common_name = taxon.preferred_common_name
        if with_term:
            common = (
                taxon.matched_term
                if taxon.matched_term not in (None, taxon.name, preferred_common_name)
                else preferred_common_name
            )
        else:
            if hierarchy:
                common = None
            else:
                common = preferred_common_name
    else:
        common = None
    name = taxon.name

    rank = taxon.rank
    rank_level = RANK_LEVELS[rank]

    if rank_level <= RANK_LEVELS["genus"]:
        name = f"*{name}*"
    if rank_level > RANK_LEVELS["species"]:
        if hierarchy:
            bold = ("\n> **", "**") if rank in TAXON_PRIMARY_RANKS else ("", "")
            name = f"{bold[0]}{name}{bold[1]}"
        elif with_rank:
            name = f"{rank.capitalize()} {name}"
    else:
        if rank in TRINOMIAL_ABBR:
            tri = name.split(" ")
            if len(tri) == 3:
                # Note: name already italicized, so close/reopen italics around insertion.
                name = f"{tri[0]} {tri[1]}* {TRINOMIAL_ABBR[rank]} *{tri[2]}"
    full_name = f"{name} ({common})" if common else name
    if not taxon.is_active:
        full_name += " \N{HEAVY EXCLAMATION MARK SYMBOL} Inactive Taxon"
    return full_name


def _full_means(taxon: Taxon):
    """Get the full establishment means for the place from listed taxa."""
    place = taxon.establishment_means and taxon.establishment_means.place
    listed_taxa = taxon.listed_taxa
    if place and listed_taxa:
        return next(
            listed_taxon
            for listed_taxon in listed_taxa
            if (listed_taxon.place and listed_taxon.place.id) == place.id
        )


def format_quality_grade(options: dict = {}):
    """Format as markdown a list of adjectives for quality grade options."""
    adjectives = []
    quality_grade = (options.get("quality_grade") or "").split(",")
    verifiable = options.get("verifiable")
    if "any" not in quality_grade:
        research = "research" in quality_grade
        needsid = "needs_id" in quality_grade
    # If specified, will override any quality_grade set already:
    if verifiable:
        if verifiable in ["true", ""]:
            research = True
            needsid = True
    if verifiable == "false":
        adjectives.append("*not Verifiable*")
    elif research and needsid:
        adjectives.append("*Verifiable*")
    else:
        if research:
            adjectives.append("*Research Grade*")
        if needsid:
            adjectives.append("*Needs ID*")
    return adjectives


class BaseFormatter:
    def format():
        raise NotImplementedError


class BaseCountFormatter(BaseFormatter):
    def count():
        raise NotImplementedError

    def description():
        raise NotImplementedError


class TaxonFormatter(BaseFormatter):
    def __init__(
        self,
        taxon: Taxon,
        lang: str = None,
        with_url: bool = True,
        matched_term: str = None,
        max_len: int = 0,
        newline: str = "\n",
    ):
        """
        Parameters
        ----------
        taxon: Taxon
            The taxon to format.

        lang: str, optional
            If specified, prefer the first name with its locale == lang instead of
            the preferred_common_name.

        matched_term: str, optional
            If specified, use instead of the taxon.matched_term.

        with_url: bool, optional
            When True, link the name to taxon.url.
        """
        self.taxon = taxon
        self.lang = lang
        self.with_url = with_url
        self.matched_term = matched_term
        self.max_len = max_len
        self.newline = newline
        self.obs_count_formatter = self.ObsCountFormatter(taxon)

    def format(self, with_ancestors: bool = True):
        """Format the taxon as markdown.

        with_ancestors: bool, optional
            When False, omit ancestors
        """
        description = self.newline.join(
            [self.format_title(), self.format_taxon_description()]
        )
        if with_ancestors and self.taxon.ancestors:
            description += " in: " + format_taxon_names(
                self.taxon.ancestors,
                hierarchy=True,
                max_len=self.max_len,
            )
        else:
            description += "."
        return description

    def format_title(self):
        """Format taxon title as Discord-like markdown.

        Returns
        -------
        str
            Like format_name(), except:

            - Append the matching term in its own parentheses after the common name
            in parentheses if the matching term is neither the scientific name nor
            common name, e.g.
            - "Pissenlits" -> "Genus *Taraxacum* (dandelions) (Pissenlits)"
            - if with_url=True, the matched term is not included in the link
            - Apply strikethrough style if the name is invalid, e.g.
            - "Picoides pubescens" ->
                "*Dryobates Pubescens* (Downy woodpecker) (~~Picoides Pubescens~~)
        """
        title = format_taxon_name(self.taxon, lang=self.lang)
        if self.with_url and self.taxon.url:
            title = format_link(title, self.taxon.url)
        # TODO: Remove workaround for outstanding pyinat issue #448 when it is resolved:
        # - https://github.com/pyinat/pyinaturalist/issues/448
        matched = self.matched_term or self.taxon.matched_term
        preferred_common_name = self.taxon.preferred_common_name
        if self.lang and self.taxon.names:
            name = next(
                iter(
                    [
                        name
                        for name in self.taxon.names
                        if name.get("locale") == self.lang
                    ]
                ),
                None,
            )
            if name:
                preferred_common_name = name.get("name")
        if matched not in (None, self.taxon.name, preferred_common_name):
            invalid_names = (
                [name["name"] for name in self.taxon.names if not name["is_valid"]]
                if self.taxon.names
                else []
            )
            if matched in invalid_names:
                matched = f"~~{matched}~~"
            title += f" ({matched})"
        return title

    def format_taxon_description(self):
        """Format the taxon description including rank, status, observation count, and means."""
        a_status_rank = self.format_taxon_status_rank()
        n_observations = self.obs_count_formatter.description()
        description = f"is {a_status_rank} with {n_observations}"
        if self.taxon.establishment_means:
            listed_taxon = _full_means(self.taxon) or self.taxon.establishment_means
            established_in_place = format_taxon_establishment_means(listed_taxon)
            if established_in_place:
                description = f"{description} {established_in_place}"
        return description

    def format_taxon_status_rank(self):
        """
        Format the taxon rank with optional status.
        """
        if self.taxon.conservation_status:
            status = self.taxon.conservation_status
            a_status = format_taxon_conservation_status(
                status, brief=True, inflect=True
            )
            a_status_rank = f"{a_status} {self.taxon.rank}"
        else:
            a_status_rank = p.a(self.taxon.rank)
        return a_status_rank

    class ObsCountFormatter(BaseCountFormatter):
        def __init__(self, taxon: Taxon):
            self.taxon = taxon

        def count(self):
            return self.taxon.observations_count

        def description(self):
            count = self.link()
            return f"{count} {p.plural('observation', count)}"

        def link(self):
            obs_count = self.count()
            obs_url = self.url()
            count = format_link(f"{obs_count:,}", obs_url)
            return count

        def url(self):
            return WWW_BASE_URL + f"/observations?taxon_id={self.taxon.id}"
