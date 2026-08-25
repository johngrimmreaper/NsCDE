Name:           NsCDE
Version:        2.3
Release:        3%{?dist}
Summary:        Not so Common Desktop Environment

License:        GPL-3.0-only
URL:            https://github.com/NsCDE/NsCDE
Source0:        %{url}/releases/download/%{version}/%{name}-%{version}.tar.gz

BuildRequires:  gcc
BuildRequires:  ksh
BuildRequires:  make
BuildRequires:  pkgconfig(x11)
BuildRequires:  pkgconfig(xext)
BuildRequires:  pkgconfig(xpm)
BuildRequires:  python3
BuildRequires:  sed
%if 0%{?suse_version}
BuildRequires:  gettext-tools
%else
BuildRequires:  gettext
%endif

Requires:       %{name}-data = %{version}-%{release}
Requires:       %{name}-icon-theme = %{version}-%{release}
Recommends:     %{name}-doc = %{version}-%{release}

Requires:       ImageMagick
Requires:       cpp
Requires:       sed
Requires:       xdotool
Requires:       xdg-utils
Requires:       xterm
Requires:       %{_bindir}/xdpyinfo
Requires:       %{_bindir}/xprop
Requires:       %{_bindir}/xrandr
Requires:       %{_bindir}/xrdb
Requires:       %{_bindir}/xrefresh
Requires:       %{_bindir}/xset

%if 0%{?suse_version}
Requires:       fvwm2
Recommends:     dejavu-fonts
Recommends:     dex
Recommends:     groff-full
Recommends:     libqt5-qtstyleplugins-platformtheme-gtk2
%else
Requires:       (fvwm or fvwm3)
Recommends:     dejavu-serif-fonts
Recommends:     dex-autostart
Recommends:     groff-base
Recommends:     qt5-qtstyleplugins
%endif

Recommends:     dunst
Recommends:     rofi
Recommends:     stalonetray
Recommends:     xclip
Recommends:     xscreensaver
Recommends:     xsettingsd
Suggests:       gkrellm
Suggests:       pcmanfm-qt
Suggests:       picom
Suggests:       qt5ct
Suggests:       qt6ct

# These components are integral parts of NsCDE and carry local changes.
Provides:       bundled(colorpicker) = 0
Provides:       bundled(pclock) = 0.13.1
Provides:       bundled(XOverrideFontCursor) = 20190901

%description
NsCDE is a retro but powerful UNIX desktop environment which resembles
CDE look (and partially feel) but with a more powerful and flexible
framework beneath-the-surface, more suited for 21st century unix-like
and Linux systems and user requirements than original CDE.

NsCDE can be considered as a heavyweight FVWM theme on steroids, but
combined with a couple other free software components and custom FVWM
applications and a lot of configuration, NsCDE can be considered a
lightweight hybrid desktop environment.


%package data
Summary:        Architecture-independent data files for %{name}
BuildArch:      noarch
Requires:       ksh
Requires:       python3
%if 0%{?suse_version}
Requires:       gettext-runtime
Requires:       python3-PyYAML
Requires:       python3-psutil
Requires:       python3-pyxdg
Requires:       python3-qt5
%else
%if 0%{?fedora} > 36
Requires:       gettext-runtime
%else
Requires:       gettext
%endif
Requires:       python3-psutil
Requires:       python3-pyxdg
Requires:       python3-qt5
Requires:       python3-yaml
%endif

%description data
This package contains architecture-independent files used by NsCDE,
including FVWM configuration, palettes, backdrops, templates, integration
files, localization files, Korn shell and Python helpers, and FvwmScripts.


%package icon-theme
Summary:        Icon theme for %{name}
BuildArch:      noarch
Requires:       hicolor-icon-theme

%description icon-theme
This package contains the NsCDE icon theme used by the desktop environment
and its XDG desktop integration.


%package doc
Summary:        Documentation for %{name}
BuildArch:      noarch

%description doc
This package contains user documentation, examples, release notes, and
HTML, plain-text, and PDF documentation for NsCDE.


%prep
%autosetup -p1


%build
%configure \
    --libdir=%{_prefix}/lib \
    --docdir=%{_docdir}/%{name} \
    --with-python-shebang=%{_bindir}/python3 \
    KSH=%{_bindir}/ksh

# Release tarballs contain generated Autotools files. Keep make from trying
# to regenerate them merely because archive extraction equalized timestamps.
touch aclocal.m4 configure
find . -name Makefile.in -exec touch {} +
%make_build


%install
%make_install KSH=%{_bindir}/ksh

# Keep architecture-independent library content under /usr/lib so the data
# subpackage can be noarch. Move the three ELF artifacts into RPM's native
# library/tool paths and use an RPM architecture name instead of uname output;
# this also makes cross-builds deterministic.
install -d %{buildroot}%{_libdir}/%{name}/%{_arch}
install -d %{buildroot}%{_libexecdir}/%{name}/%{_arch}

find %{buildroot}%{_prefix}/lib/%{name} \
    -path '*/Linux_*/*' -type f -name XOverrideFontCursor.so \
    -exec mv -t %{buildroot}%{_libdir}/%{name}/%{_arch} {} +

find %{buildroot}%{_libexecdir}/%{name} \
    -path '*/Linux_*/*' -type f \
    \( -name colorpicker -o -name fpclock \) \
    -exec mv -t %{buildroot}%{_libexecdir}/%{name}/%{_arch} {} +

# These dispatchers are architecture-specific because they name the native
# paths above, so they belong in the main package with the ELF artifacts.
sed -i \
    's#${NSCDE_TOOLSDIR}/${OS_PLUS_MACHINE_ARCH}/colorpicker#${NSCDE_TOOLSDIR}/%{_arch}/colorpicker#g' \
    %{buildroot}%{_libexecdir}/%{name}/colorpicker
sed -i \
    's#${NSCDE_TOOLSDIR}/${NSCDE_OS}_${MARCH}/fpclock#${NSCDE_TOOLSDIR}/%{_arch}/fpclock#g' \
    %{buildroot}%{_libexecdir}/%{name}/fpclock
sed -i \
    's#\$NSCDE_LIBDIR/\$OS_PLUS_MACHINE_ARCH/XOverrideFontCursor\.so#%{_libdir}/%{name}/%{_arch}/XOverrideFontCursor.so#g' \
    %{buildroot}%{_prefix}/lib/%{name}/fvwm-modules/FvwmScript

find \
    %{buildroot}%{_prefix}/lib/%{name} \
    %{buildroot}%{_libexecdir}/%{name} \
    -type d -empty -delete

# Python modules are imported, not executed directly.
find %{buildroot}%{_prefix}/lib/%{name}/python \
    -type f -name '*.py' -exec chmod 0644 {} +
chmod 0644 %{buildroot}%{_libexecdir}/%{name}/style_managers.shlib

# The installed LICENSE is a duplicate of COPYING; %%license installs it in
# the standard per-subpackage license directories instead.
rm -f %{buildroot}%{_docdir}/%{name}/LICENSE

%find_lang %{name} --all-name


%check
test -x %{buildroot}%{_libdir}/%{name}/%{_arch}/XOverrideFontCursor.so
test -x %{buildroot}%{_libexecdir}/%{name}/%{_arch}/colorpicker
test -x %{buildroot}%{_libexecdir}/%{name}/%{_arch}/fpclock
grep -Fq '${NSCDE_TOOLSDIR}/%{_arch}/colorpicker' \
    %{buildroot}%{_libexecdir}/%{name}/colorpicker
grep -Fq '${NSCDE_TOOLSDIR}/%{_arch}/fpclock' \
    %{buildroot}%{_libexecdir}/%{name}/fpclock
grep -Fq '%{_libdir}/%{name}/%{_arch}/XOverrideFontCursor.so' \
    %{buildroot}%{_prefix}/lib/%{name}/fvwm-modules/FvwmScript
test -z "$(find %{buildroot} -path '*/Linux_*/*' -print -quit)"


%files
%license COPYING
%{_bindir}/nscde
%{_bindir}/nscde_fvwmclnt
%{_datadir}/applications/nscde-*.desktop
%{_datadir}/xsessions/nscde.desktop
%dir %{_libdir}/%{name}
%dir %{_libdir}/%{name}/%{_arch}
%{_libdir}/%{name}/%{_arch}/XOverrideFontCursor.so
%dir %{_libexecdir}/%{name}
%dir %{_libexecdir}/%{name}/%{_arch}
%{_libexecdir}/%{name}/%{_arch}/colorpicker
%{_libexecdir}/%{name}/%{_arch}/fpclock
%{_libexecdir}/%{name}/colorpicker
%{_libexecdir}/%{name}/fpclock
%{_prefix}/lib/%{name}/fvwm-modules/FvwmScript

%files data -f %{name}.lang
%license COPYING
%config(noreplace) %{_sysconfdir}/xdg/menus/nscde-applications.menu
%{_datadir}/desktop-directories/nscde-*.directory
%{_datadir}/%{name}/
%{_prefix}/lib/%{name}/
%exclude %{_prefix}/lib/%{name}/fvwm-modules/FvwmScript
%exclude %{_libdir}/%{name}/%{_arch}/
%{_libexecdir}/%{name}/
%exclude %{_libexecdir}/%{name}/%{_arch}/
%exclude %{_libexecdir}/%{name}/colorpicker
%exclude %{_libexecdir}/%{name}/fpclock

%files icon-theme
%license COPYING
%{_datadir}/icons/%{name}/

%files doc
%license COPYING
%doc %{_docdir}/%{name}/

%changelog
* Sun Aug 16 2026 John Grim Reaper <JohnGrimmReaper@disroot.org> - 2.3-UNRELEASED
- Split architecture-independent data, icon theme, and documentation packages
- Keep only native helpers, their dispatchers, and launchers in the main package
- Relocate ELF artifacts to deterministic RPM architecture paths
- Normalize Python module permissions and modernize package metadata

* Fri Jun 16 2023 Hegel3DReloaded <nscde@protonmail.com>  - 2.3-3
- Portability and bug fixes
- Misc small fixes
- Release 2.3

* Mon Jun 5 2023 Hegel3DReloaded <nscde@protonmail.com>  - 2.3-2
- Font and Color Style Manager: reload new themes without FVWM restart
- Qt6 integration support
- Optional Picom X Compositor internal support
- Thunderbird 102+ CSS theme integration support
- Firefox up to 113+ CSS theme integration support
- Font and Color Style Manager reshape, add integrations as separate dialog
- (De)Iconify X11 freeze glitch fvwm workaround
- Front Panel initial placement fix instead of workaround
- Fix GWM FvwmScript segfault on exit
- More missing icons in XDG icon theme
- Handle gsettings org.gnome.desktop.interface color-scheme
- Xscreensaver 6.X support
- Add detailed X resources for xcalc and some old Athena based apps
- Tuning X resources for more old apps
- Font and Color Style Manager: remember widget integration options
- GTK3 theme fixes: treat nasty header bar as toolbar
- Initial setup: add detailed integration questions, Qt6 support
- Front Panel clock: triangle hour and minute hands to match original
- GWMPager as popup on workspace change in no-page mode
- Fixed some easy-to-make keyboard shortcuts accidental calls
- Firefox and Thunderbird user.js additions for nice initial look & feel
- Thunderbird HTML compose window toolbar fix
- Docs update, many portability fixes, misc fixes, some typo fixes

* Mon Oct 31 2022 Hegel3DReloaded <nscde@protonmail.com> - 2.3-1
- Start with 2.3
- Add groff-full / groff-base as dependency for panel and subpanel help

* Sun Jul 24 2022 Hegel3DReloaded <nscde@protonmail.com> - 2.2.6
- Add kcalc colors tom match dtcalc (colormgr.local)
- Fix rofi and dunst themes to work with new versions of programs
- NsCDE .desktop files renamed to conform to standards
- Front Panel on top of the screen possibility implemented. This
  can be achieved with "InfoStoreAdd frontpanel.on.top 1" in
  ~/.NsCDE/NsCDE.conf.
- Icon theme updates
- CSS: support firefox 100+
- Consolidate GTK2 and GTK3 engine css files, add some fixes
  and match colors more correctly
- Added Common User Access (CUA) key bindings. This is now
  default key binding set in NsCDE. Old key bindings scheme
  now called "nscde1x" can be used in ~/.NsCDE/NsCDE.conf
  with the "InfoStoreAdd kbd_bind_set nscde1x" - this can also
  be configured now with Keyboard Style Manager
- Keyboard Style Manager addons, Mouse Style Manager fixes
- Building: add --with-python-shebang="STRING" in configure
  to allow user to override strange alternatives managers on
  some systems
- Reorganize f_PolkitAgent to be more portable and stable
- Kvantum: Reshape in more Motif style Qt5 Combo Box
- More Firefox CSS updates
- Documentation updates for all of the above

* Thu Jul 14 2022 Hegel3DReloaded <nscde@protonmail.com> - 2.2.5
- Works on keybindings continued

* Mon Jul 11 2022 Hegel3DReloaded <nscde@protonmail.com> - 2.2.4
- Works on CUA keybinding set

* Tue Mar 22 2022 Hegel3DReloaded <nscde@protonmail.com> - 2.1-4
- New colormgr.local / colormgr.addons scheme
- Introduce key binding sets
- Backup old gtk and qt configs during bootstrap
- Optionally specify alternative root setter for fvwm3 non-global monitors
- Inject new NSCDE_VERSION on restart after upgrade
- Various fixes
- Qt5 Kvantum engine support
- Update docs

* Thu Jan 6 2022 Hegel3DReloaded <nscde@protonmail.com> - 2.0-6
- Fix system Subpanels.actions S10 help backspaces
- Fix move first item to the end double copy on the subpanels

* Wed Jan 5 2022 Hegel3DReloaded <nscde@protonmail.com> - 2.0-5
- Fix generate_subpanels backslash and quoting

* Tue Dec 21 2021 Hegel3DReloaded <nscde@protonmail.com> - 2.0-4
- Release NsCDE 2.0
- Fix Qt5 qt5ct.conf new fonts handling
- Update fontsets for higher resolutions
- Add more handy key bindings into style managers
- Documentation now has descriptions of XDG subsystems in NsCDE
- Support for more terminal emulators in colormgr.local and fontmgr.local
- Illustrated documentation
- Smart XDG paths from configure.ac
- Front Panel and Subpanels smart contextual Help
- Correct screen calculation for GWM under FVWM3 with multiple monitors
- Misc minor fixes

* Fri Dec 3 2021 Hegel3DReloaded <nscde@protonmail.com> - 2.0-3
- Introduce Front Panel Icon Manager
- Update docs and locales
- Misc minor fixes
- Move Front Panel icons feature
- Rename Subpanel Items feature
- Input checking

* Tue Nov 9 2021 Hegel3DReloaded <nscde@protonmail.com> - 2.0
- First RPM package, working example
