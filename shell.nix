{ pkgs ? import <nixpkgs> {} }:
pkgs.mkShell {
  packages = [
    (pkgs.python3.withPackages (ps: with ps; [ pillow numpy nbtlib ]))
    pkgs.jdk25_headless   # Minecraft 26.x needs Java 25 (also runs 1.21.x)
  ];
}
