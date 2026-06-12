pkgname=keystone-osk
pkgver=0.1.0
pkgrel=1
pkgdesc="Practical on-screen keyboard for Linux desktops"
arch=("any")
url="https://github.com/svan71/keystone-osk"
license=("GPL-3.0-or-later")
depends=("python" "pyside6" "ydotool")
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
}
