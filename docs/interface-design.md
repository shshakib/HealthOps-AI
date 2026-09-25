# Interface design

The September 2026 refresh treats HealthOps as a working research tool. The main
content is the patient record, the trial requirements, and the review decision.

- IBM Plex Sans is bundled locally in regular, medium, and semibold weights.
  Supporting text is at least 12px; primary form labels and body text are larger.
- Off-white canvas, white working surfaces, dark ink text, and a restrained blue
  accent. Blue identifies actions and selection. Green, amber, and red identify
  findings and always appear with text labels.
- The HealthOps mark uses two record columns joined into an H. Functional outline
  icons identify navigation and actions; decorative metric icons were removed.
- Workspace counts share a single strip. Patient lists and evidence rows use
  separators, with modest corner rounding and clear active states.
- Forms, decisions, dialogs, assistant responses, login, and admin pages share
  the same type, spacing, and control styles. Keyboard focus remains visible,
  with a skip link that preserves the saved assessment URL.
- At narrower widths, navigation moves above the content and columns stack.
  Core actions use 44px controls. Supporting copy stays readable rather than
  being reduced to fit the viewport.

## References

These informed the design decisions; HealthOps does not reproduce their branding
or claim their accessibility certification or endorsement.

- [NHS typography](https://service-manual.nhs.uk/design-system/styles/typography):
  consistent heading hierarchy and readable supporting text.
- [NHS colour guidance](https://service-manual.nhs.uk/design-system/styles/colour):
  restrained functional colour and contrast.
- [IBM Carbon data tables](https://carbondesignsystem.com/components/data-table/usage/):
  clear rows, useful spacing, and progressive disclosure of evidence.
- [IBM Plex Sans](https://fontsource.org/fonts/ibm-plex-sans): locally served font
  files under the SIL Open Font License, included with the build.

The implementation lives in `frontend/src/style.css`, `BrandMark.jsx`, and the
existing React screens. Screening logic, account permissions, and AI tools are
unchanged. The README uses actual captures of this interface from the isolated
September 24 recording workspace. The full application walkthrough shows the
same design. Older release notes and media describe their original releases.
