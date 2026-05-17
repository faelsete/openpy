# Skill: Transcrição de Áudio

## Contexto
O usuário quer transcrever áudio para texto.

## Ferramentas disponíveis

### Whisper (OpenAI) — Recomendado
```bash
# Verificar instalação
whisper --help
pip install openai-whisper

# Transcrever
whisper arquivo.mp3 --language pt --model medium --output_format txt
whisper arquivo.mp3 --language pt --model large --output_format srt  # com legendas
```

### FFmpeg — Para conversão prévia
```bash
# Converter para formato compatível
ffmpeg -i input.mp4 -vn -ar 16000 -ac 1 output.wav
# Extrair áudio de vídeo
ffmpeg -i video.mp4 -q:a 0 -map a audio.mp3
```

## Critérios de sucesso
- Arquivo de saída gerado com conteúdo legível
- Idioma detectado corretamente
- Tempo de processamento aceitável

## Modelos Whisper por qualidade/velocidade
- tiny: mais rápido, menos preciso
- base: bom compromisso para testes
- medium: recomendado para português
- large: mais preciso, mais lento
