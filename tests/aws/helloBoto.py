import boto3

polly = boto3.client('polly')
result = polly.synthesize_speech(Text='Butt stank supreme!', OutputFormat='mp3', VoiceId='Joanna')
audio = result['AudioStream'].read()
with open('helloworld.mp3', 'wb') as f:
    f.write(audio)
