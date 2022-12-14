from dataclasses import dataclass
import enum
from typing import ClassVar, Literal, overload
import xml.etree.ElementTree as ET

from scm_staging.obs import Osc
from .xml_factory import MetaMixin, StrElementField


ROLE_T = Literal["bugowner", "maintainer"]


@enum.unique
class PersonRole(enum.StrEnum):
    BUGOWNER = enum.auto()
    MAINTAINER = enum.auto()
    READER = enum.auto()


@dataclass(frozen=True)
class Person(MetaMixin):
    userid: str
    role: PersonRole = PersonRole.MAINTAINER

    _element_name: ClassVar[str] = "person"


@dataclass(frozen=True)
class PathEntry(MetaMixin):
    project: str
    repository: str

    _element_name: ClassVar[str] = "path"


@dataclass(frozen=True)
class Repository(MetaMixin):
    name: str
    path: list[PathEntry] | None = None
    arch: list[str] | None = None

    _element_name: ClassVar[str] = "repository"


@dataclass(frozen=True)
class Project(MetaMixin):
    name: str
    title: StrElementField
    description: StrElementField = StrElementField("")

    person: list[Person] | None = None
    repository: list[Repository] | None = None

    _element_name: ClassVar[str] = "project"


@dataclass(frozen=True)
class Package:
    name: str
    title: str
    description: str = ""

    scmsync: str | None = None

    _element_name: ClassVar[str] = "package"

    @property
    def meta(self) -> ET.Element:
        (pkg_conf := ET.Element(Package._element_name)).attrib["name"] = self.name
        (title := ET.Element("title")).text = self.title
        (descr := ET.Element("description")).text = self.description
        pkg_conf.append(title)
        pkg_conf.append(descr)
        if self.scmsync:
            (scmsync := ET.Element("scmsync")).text = self.scmsync
            pkg_conf.append(scmsync)

        return pkg_conf


@overload
async def send_meta(osc: Osc, *, prj: Project) -> None:
    ...


@overload
async def send_meta(osc: Osc, *, prj: Project, pkg: Package) -> None:
    ...


@overload
async def send_meta(osc: Osc, *, prj_name: str, prj_meta: ET.Element) -> None:
    ...


@overload
async def send_meta(
    osc: Osc, *, prj_name: str, pkg_name: str, pkg_meta: ET.Element
) -> None:
    ...


async def send_meta(
    osc: Osc,
    *,
    prj: Project | None = None,
    prj_name: str | None = None,
    prj_meta: ET.Element | None = None,
    pkg: Package | None = None,
    pkg_name: str | None = None,
    pkg_meta: ET.Element | None = None,
) -> None:
    route = "/source/"

    if prj and pkg:
        route += f"{prj.name}/{pkg.name}"
        meta = pkg.meta
    elif prj and not pkg:
        route += prj.name
        meta = prj.meta
    elif prj_name and pkg_name and pkg_meta:
        route += f"{prj_name}/{pkg_name}"
        meta = pkg_meta
    elif prj_name and prj_meta:
        route += prj_name
        meta = prj_meta
    else:
        assert False, "Invalid parameter combination"

    route += "/_meta"

    await osc.api_request(route=route, payload=ET.tostring(meta), method="PUT")


@overload
async def delete(osc: Osc, *, prj: Project | str, force: bool = False) -> None:
    ...


@overload
async def delete(
    osc: Osc, *, prj: Project | str, pkg: Package | str, force: bool = False
) -> None:
    ...


async def delete(
    osc: Osc,
    *,
    prj: Project | str,
    pkg: Package | str | None = None,
    force: bool = False,
) -> None:
    prj_name = prj.name if isinstance(prj, Project) else prj
    route = f"/source/{prj_name}/"
    if pkg:
        route += pkg.name if isinstance(pkg, Package) else pkg

    await osc.api_request(
        route, method="DELETE", params={"force": "1"} if force else None
    )
