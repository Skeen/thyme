{
  description = "Traggo to Redmine integration";

  inputs = {
    nixpkgs = {
      url = "github:NixOS/nixpkgs/nixos-unstable";
    };
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = {
    self,
    nixpkgs,
    poetry2nix,
  }: let
    supportedSystems = ["x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin"];
    forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    pkgsFor = system: nixpkgs.legacyPackages.${system};

    poetry_overrides = pkgs: self: super: {
      # Use nixpkgs versions for pydantic stack to avoid build issues and conflicts
      pydantic = pkgs.python311Packages.pydantic;
      pydantic-core = pkgs.python311Packages.pydantic-core;
      typing-extensions = pkgs.python311Packages.typing-extensions;
      typing-inspection = pkgs.python311Packages.typing-inspection;

      # Fix python-redmine build
      python-redmine = super.python-redmine.overridePythonAttrs (old: {
        nativeBuildInputs =
          (old.nativeBuildInputs or [])
          ++ [
            pkgs.python311Packages.setuptools
            pkgs.python311Packages.wheel
          ];
      });
    };
  in {
    packages = forAllSystems (system: let
      pkgs = pkgsFor system;
      p2n = poetry2nix.lib.mkPoetry2Nix {inherit pkgs;};
    in {
      thyme = p2n.mkPoetryApplication {
        projectDir = ./.;
        python = pkgs.python311;
        preferWheels = true;
        overrides = p2n.defaultPoetryOverrides.extend (poetry_overrides pkgs);
      };
      default = self.packages.${system}.thyme;
    });

    devShells = forAllSystems (system: let
      pkgs = pkgsFor system;
      p2n = poetry2nix.lib.mkPoetry2Nix {inherit pkgs;};
    in {
      default = pkgs.mkShell {
        packages = [
          (p2n.mkPoetryEnv {
            projectDir = ./.;
            python = pkgs.python311;
            preferWheels = true;
            overrides = p2n.defaultPoetryOverrides.extend (poetry_overrides pkgs);
            editablePackageSources = {
              thyme = ./thyme;
            };
          })
          pkgs.poetry
        ];
      };
    });
  };
}
