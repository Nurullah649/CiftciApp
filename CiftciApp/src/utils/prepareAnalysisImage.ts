import * as ImageManipulator from 'expo-image-manipulator';

/** Yüklemeden önce fotoğrafı küçültür (nginx 413 önlenir). */
export async function prepareAnalysisImage(uri: string): Promise<string> {
  const result = await ImageManipulator.manipulateAsync(
    uri,
    [{ resize: { width: 1024 } }],
    { compress: 0.72, format: ImageManipulator.SaveFormat.JPEG },
  );
  return result.uri;
}
