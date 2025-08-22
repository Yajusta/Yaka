# Composants utilisés dans l'application
$usedComponents = @(
    "button",
    "input", 
    "label",
    "textarea",
    "card",
    "badge",
    "avatar",
    "dialog",
    "select",
    "alert"
)

# Supprimer tous les composants sauf ceux utilisés
Get-ChildItem "src/components/ui/*.tsx" | ForEach-Object {
    $componentName = $_.BaseName
    if ($usedComponents -notcontains $componentName) {
        Write-Host "Suppression de $componentName.tsx"
        Remove-Item $_.FullName
    } else {
        Write-Host "Conservation de $componentName.tsx"
    }
}

Write-Host "Nettoyage terminé !" 