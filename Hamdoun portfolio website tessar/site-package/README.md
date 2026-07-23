# BlackLarch website — clean upload naar GitHub

Dit pakket bevat de volledige site: `index.html`, `support.js`, `deck-stage.js`,
`Workflow Presentatie.dc.html`, `assets/`, `uploads/`.

## Repo volledig vervangen (oude bestanden ook weg)

In je lokale kopie van de repo:

```bash
git clone <jouw-repo-url> repo
cd repo

# alles weghalen behalve .git
git rm -rf --ignore-unmatch .
git clean -fdx

# pak dit zip-pakket uit in deze map (index.html, support.js, deck-stage.js,
# Workflow Presentatie.dc.html, assets/, uploads/ moeten in de root komen)

git add -A
git commit -m "BlackLarch: nieuwe site"
git push
```

Als de repo GitHub Pages gebruikt vanaf `main` / root, staat de site na de
push automatisch live met alleen de nieuwe bestanden — niets van de oude
Hamdoun-versie blijft over.

## Alternatief: via de GitHub-website

Verwijder in de repo (op github.com) eerst handmatig alle oude
bestanden/mappen, commit die verwijdering, upload dan pas de nieuwe
bestanden. Los uploaden zonder eerst te verwijderen overschrijft alleen
gelijknamige bestanden.

## Inhoud

- `index.html` — de homepage (BlackLarch, NL/EN, 5 projectdemo's)
- `Workflow Presentatie.dc.html` — losse slide-deck voor de afspraakopvolging
- `deck-stage.js`, `support.js` — draaien de pagina's, niet aanpassen
- `assets/` — logo (icoon + wordmark, licht/donker)
- `uploads/DSC08075.jpg` — achtergrondfoto in de presentatie
