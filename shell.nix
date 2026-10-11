{ pkgs ? import <nixpkgs> {} }:
pkgs.mkShell {
  packages = [
    (pkgs.python3.withPackages (ps: with ps; [ pillow numpy nbtlib ]))
    pkgs.jdk21_headless
  ];
}
