# Builds Keystone from this checkout. The AUR package uses its own PKGBUILD
# that fetches a released tarball instead of building from $startdir.
pkgname=keystone-osk
pkgver=0.9.0
pkgrel=1
pkgdesc="Practical on-screen keyboard for Linux desktops"
arch=("any")
url="https://github.com/svan71/keystone-osk"
license=("GPL-3.0-or-later")
# ydotool is invoked as a subprocess by keystone_osk/backend.py, so namcap
# cannot see it and will report it as possibly unneeded. It is required.
depends=("python" "pyside6" "ydotool" "hicolor-icon-theme")
optdepends=()
makedepends=("python-build" "python-installer" "python-setuptools" "python-wheel" "desktop-file-utils")
source=()
sha256sums=()

build() {
  cd "$startdir/source"
  python -m build --wheel --no-isolation
}

package() {
  cd "$startdir/source"
  python -m installer --destdir="$pkgdir" dist/*.whl

  cd "$startdir"
  install -Dm644 source/LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
  install -Dm644 live-install/applications/keystone-osk.desktop "$pkgdir/usr/share/applications/keystone-osk.desktop"
  install -Dm644 live-install/icons/hicolor/256x256/apps/keystone.png "$pkgdir/usr/share/icons/hicolor/256x256/apps/keystone.png"
  install -Dm644 live-install/icons/hicolor/256x256/apps/keystone-transparent.png "$pkgdir/usr/share/icons/hicolor/256x256/apps/keystone-transparent.png"
  install -Dm644 packaging/io.github.svan71.keystone-osk.metainfo.xml "$pkgdir/usr/share/metainfo/io.github.svan71.keystone-osk.metainfo.xml"
}
