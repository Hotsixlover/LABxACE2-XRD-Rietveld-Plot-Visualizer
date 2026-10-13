# SPDX-License-Identifier: GPL-2.0-or-later
[CmdletBinding()]
param(
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$nativeDirectory = Join-Path $projectDirectory 'xrd_rietveld_manager\native'
$sourcePath = Join-Path $nativeDirectory 'xrd_native.cpp'
$outputPath = Join-Path $nativeDirectory 'xrd_native.dll'
$buildDirectory = Join-Path $nativeDirectory 'build'
$objectPath = Join-Path $buildDirectory 'xrd_native.obj'

if ($Clean -and (Test-Path -LiteralPath $buildDirectory)) {
    Remove-Item -LiteralPath $buildDirectory -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $buildDirectory | Out-Null

$cmake = Get-Command cmake -ErrorAction SilentlyContinue
if ($cmake) {
    & $cmake.Source -S $nativeDirectory -B $buildDirectory -DCMAKE_BUILD_TYPE=Release
    if ($LASTEXITCODE -ne 0) { throw 'CMake configure failed.' }
    & $cmake.Source --build $buildDirectory --config Release
    if ($LASTEXITCODE -ne 0) { throw 'CMake build failed.' }
} else {
    $compiler = Get-Command cl.exe -ErrorAction SilentlyContinue
    $vcvars = $null
    if (-not $compiler) {
        $vswhereCandidates = @(
            "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe",
            "$env:ProgramFiles\Microsoft Visual Studio\Installer\vswhere.exe"
        )
        $vswhere = $vswhereCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        if ($vswhere) {
            $installation = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
            if ($installation) {
                $candidate = Join-Path $installation 'VC\Auxiliary\Build\vcvars64.bat'
                if (Test-Path -LiteralPath $candidate) { $vcvars = $candidate }
            }
        }
    }

    if ($compiler) {
        & $compiler.Source /nologo /std:c++17 /O2 /EHsc /W4 /MT /LD $sourcePath "/Fo:$objectPath" "/Fe:$outputPath"
        if ($LASTEXITCODE -ne 0) { throw 'MSVC build failed.' }
    } elseif ($vcvars) {
        $compileCommand = '"{0}" && cl /nologo /std:c++17 /O2 /EHsc /W4 /MT /LD "{1}" /Fo:"{2}" /Fe:"{3}"' -f $vcvars, $sourcePath, $objectPath, $outputPath
        & cmd.exe /d /s /c $compileCommand
        if ($LASTEXITCODE -ne 0) { throw 'MSVC build failed.' }
    } else {
        $gpp = Get-Command g++.exe -ErrorAction SilentlyContinue
        if (-not $gpp) {
            throw 'No C++ compiler was found. Install Visual Studio Build Tools (Desktop development with C++) or CMake plus a C++17 compiler.'
        }
        & $gpp.Source -std=c++17 -O3 -shared -static-libgcc -static-libstdc++ -o $outputPath $sourcePath
        if ($LASTEXITCODE -ne 0) { throw 'MinGW build failed.' }
    }
}

if (-not (Test-Path -LiteralPath $outputPath)) {
    throw "Build completed but the DLL was not found: $outputPath"
}
Write-Host "Native accelerator built: $outputPath"
